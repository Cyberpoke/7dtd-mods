using System.Collections.Generic;
using System.IO;
using Platform;
using UnityEngine;

namespace QuickStackPlus
{
    public static class QuickStackService
    {
        const ushort StorageChannel = 0;
        const ushort CollectChannel = 1;

        static readonly HashSet<int> RunningPlayers = new HashSet<int>();
        static readonly HashSet<ILockTarget> HeldTargets = new HashSet<ILockTarget>();

        public static QuickStackResult Run(
            World world,
            EntityPlayer player,
            ClientInfo client,
            PlatformUserIdentifierAbs userId,
            QuickStackMode mode)
        {
            var result = new QuickStackResult
            {
                Mode = mode,
                RadiusMeters = QuickStackConfig.ClampRadius(QuickStackConfig.RadiusMeters)
            };

            if (world == null || player == null || player.bag == null || player.IsDead())
            {
                result.Outcome = IsBoxMode(mode)
                    ? QuickStackOutcome.NoStorage
                    : QuickStackOutcome.NoVehicle;
                return result;
            }

            if (!RunningPlayers.Add(player.entityId))
            {
                result.Outcome = IsBoxMode(mode)
                    ? QuickStackOutcome.Busy
                    : QuickStackOutcome.VehicleBusy;
                return result;
            }

            try
            {
                // The dedicated server's live entity bag is the spawn snapshot.
                // The client's backpack is uploaded into latestPlayerData.bagData.
                if (!(player is EntityPlayerLocal))
                {
                    PullBag(player, client);
                }

                if (IsBoxMode(mode))
                {
                    StackToBoxes(world, player, userId, mode == QuickStackMode.NearbyType, result);
                }
                else
                {
                    StackToVehicle(world, player, userId, mode == QuickStackMode.VehicleAll, result);
                }

                PushBag(player, client);
                Log.Out("[QuickStackPlus] " + QuickStackMessages.Format(result) +
                    " player=" + player.entityId);
                return result;
            }
            finally
            {
                RunningPlayers.Remove(player.entityId);
            }
        }

        static void PullBag(EntityPlayer player, ClientInfo client)
        {
            MemoryStream blob = client?.latestPlayerData?.bagData;
            if (blob == null || blob.Length == 0)
            {
                return;
            }

            StreamUtils.FromBlob(blob, reader =>
            {
                player.bag.ReadInto(reader, StreamModeRead.FromClient);
            });
        }

        static void PushBag(EntityPlayer player, ClientInfo client)
        {
            if (client?.latestPlayerData == null || player.bag == null)
            {
                return;
            }

            client.latestPlayerData.bagData = StreamUtils.ToBlob(writer =>
            {
                player.bag.Write(writer, StreamModeWrite.Persistency);
            });
            client.latestPlayerData.bModifiedSinceLastSave = true;
        }

        static bool IsBoxMode(QuickStackMode mode)
        {
            return mode == QuickStackMode.Nearby || mode == QuickStackMode.NearbyType;
        }

        static void StackToBoxes(
            World world,
            EntityPlayer player,
            PlatformUserIdentifierAbs userId,
            bool matchType,
            QuickStackResult result)
        {
            int skippedBusy = 0;
            List<BoxTarget> boxes = FindBoxes(world, player, userId, result, ref skippedBusy);
            var held = new List<ILockTarget>();
            var open = new List<BoxTarget>();
            try
            {
                for (int i = 0; i < boxes.Count; i++)
                {
                    ILockTarget target = boxes[i].Storage;
                    if (!TryHold(target, StorageChannel))
                    {
                        skippedBusy++;
                        continue;
                    }

                    held.Add(target);
                    open.Add(boxes[i]);
                }

                if (open.Count == 0)
                {
                    result.Outcome = skippedBusy > 0
                        ? QuickStackOutcome.Busy
                        : QuickStackOutcome.NoStorage;
                    return;
                }

                bool hadMatchingType;
                int containers = MoveFromBackpack(
                    player.bag,
                    open,
                    matchType ? MoveStyle.TypeThenEmpty : MoveStyle.TopOff,
                    result,
                    out hadMatchingType);
                result.ContainerCount = containers;
                if (result.MovedItemCount > 0)
                {
                    result.Outcome = QuickStackOutcome.Moved;
                }
                else if (matchType && hadMatchingType)
                {
                    result.Outcome = QuickStackOutcome.NoRoom;
                }
                else
                {
                    result.Outcome = QuickStackOutcome.NoMatch;
                }
            }
            finally
            {
                Release(held);
            }
        }

        static void StackToVehicle(
            World world,
            EntityPlayer player,
            PlatformUserIdentifierAbs userId,
            bool allowEmptySlots,
            QuickStackResult result)
        {
            bool anyOwned = false;
            EntityVehicle vehicle = FindVehicle(world, player, userId, result.RadiusMeters, ref anyOwned);
            if (vehicle == null)
            {
                result.Outcome = anyOwned ? QuickStackOutcome.VehicleBusy : QuickStackOutcome.NoVehicle;
                return;
            }

            var held = new List<ILockTarget>();
            try
            {
                if (!TryHold(vehicle, StorageChannel))
                {
                    result.Outcome = QuickStackOutcome.VehicleBusy;
                    return;
                }

                held.Add(vehicle);
                if (LockManager.Instance.IsLockedServer(vehicle, CollectChannel))
                {
                    result.Outcome = QuickStackOutcome.VehicleBusy;
                    return;
                }
                var targets = new List<BoxTarget>
                {
                    new BoxTarget(null, vehicle, 0f)
                };
                int changed = MoveFromBackpack(
                    player.bag,
                    targets,
                    allowEmptySlots ? MoveStyle.AllThenEmpty : MoveStyle.TopOff,
                    result,
                    out _);
                if (changed > 0)
                {
                    vehicle.SetBagModified();
                }

                if (result.MovedItemCount > 0)
                {
                    result.ContainerCount = 1;
                    result.Outcome = QuickStackOutcome.Moved;
                }
                else
                {
                    result.Outcome = allowEmptySlots
                        ? QuickStackOutcome.NoRoom
                        : QuickStackOutcome.NoMatch;
                }
            }
            finally
            {
                Release(held);
            }
        }

        enum MoveStyle
        {
            TopOff,
            TypeThenEmpty,
            AllThenEmpty
        }

        static int MoveFromBackpack(
            Bag bag,
            List<BoxTarget> targets,
            MoveStyle style,
            QuickStackResult result,
            out bool hadMatchingType)
        {
            var changedSlots = new HashSet<int>();
            var changedTargets = new HashSet<int>();
            var eligible = new List<int>();
            ItemStackGrid grid = bag.ItemGrid;
            hadMatchingType = false;

            for (int slot = 0; slot < grid.Length; slot++)
            {
                if (grid.IsSlotLocked(slot))
                {
                    continue;
                }

                ItemStack stack = grid[slot];
                if (stack == null || stack.IsEmpty())
                {
                    continue;
                }

                eligible.Clear();
                for (int i = 0; i < targets.Count; i++)
                {
                    if (!CanEnter(stack, targets[i]))
                    {
                        continue;
                    }

                    if (style == MoveStyle.TypeThenEmpty && !ContainsType(targets[i], stack))
                    {
                        continue;
                    }

                    eligible.Add(i);
                }

                if (style == MoveStyle.TypeThenEmpty)
                {
                    if (eligible.Count == 0)
                    {
                        continue;
                    }

                    hadMatchingType = true;
                }

                int before = stack.count;
                for (int n = 0; n < eligible.Count && stack.count > 0; n++)
                {
                    int index = eligible[n];
                    (bool anyMoved, bool _) = TryStack(targets[index], stack);
                    if (anyMoved)
                    {
                        changedTargets.Add(index);
                    }
                }

                if (stack.count <= 0)
                {
                    ClearSlot(stack);
                }
                else if (style != MoveStyle.TopOff)
                {
                    for (int n = 0; n < eligible.Count && stack.count > 0; n++)
                    {
                        int index = eligible[n];
                        if (PlaceInEmpty(targets[index], stack))
                        {
                            changedTargets.Add(index);
                            break;
                        }
                    }
                }

                int left = stack.IsEmpty() ? 0 : stack.count;
                if (left != before)
                {
                    changedSlots.Add(slot);
                    result.MovedItemCount += before - left;
                }
            }

            foreach (int slot in changedSlots)
            {
                result.Slots.Add(new SlotChange(slot, grid.GetItemClone(slot)));
            }

            return changedTargets.Count;
        }

        // Identity test from ItemStack.CanStackWith, without the "room left in the stack" check.
        // Quality and mods are not compared; TryStackItem does not compare them either.
        static bool SameItemType(ItemStack source, ItemStack existing)
        {
            ItemValue left = source?.itemValue;
            ItemValue right = existing?.itemValue;
            if (left == null || right == null || left.type == 0 || left.type != right.type)
            {
                return false;
            }

            if (left.type < Block.ItemsStartHere)
            {
                return left.IsShapeHelperBlock || left.TextureFullArray == right.TextureFullArray;
            }

            return true;
        }

        static bool ContainsType(BoxTarget target, ItemStack source)
        {
            ItemStackGrid grid = target.Storage?.ItemGrid;
            if (grid == null)
            {
                return false;
            }

            for (int i = 0; i < grid.Length; i++)
            {
                ItemStack slot = grid[i];
                if (slot != null && !slot.IsEmpty() && SameItemType(source, slot))
                {
                    return true;
                }
            }

            return false;
        }

        static bool CanEnter(ItemStack stack, BoxTarget target)
        {
            XUiC_ItemStack.StackLocationTypes location = target.Vehicle != null
                ? target.Vehicle.bag.StackLocation
                : XUiC_ItemStack.StackLocationTypes.LootContainer;
            return stack.CanMoveTo(location);
        }

        // Same rule as the vanilla stack button: TryStackItem matches item type and
        // only fills a stack that still has room (ItemStack.CanStackPartly / MaxCount).
        static (bool anyMoved, bool allMoved) TryStack(BoxTarget target, ItemStack stack)
        {
            if (target.Vehicle != null)
            {
                return target.Vehicle.bag.TryStackItem(0, stack);
            }

            return target.Storage.TryStackItem(0, stack);
        }

        static bool PlaceInEmpty(BoxTarget target, ItemStack stack)
        {
            ItemStackGrid grid = target.Vehicle != null
                ? target.Vehicle.bag?.ItemGrid
                : target.Storage?.ItemGrid;
            if (grid == null)
            {
                return false;
            }
            for (int i = 0; i < grid.Length; i++)
            {
                if (grid.IsSlotLocked(i) || !grid[i].IsEmpty())
                {
                    continue;
                }

                grid.SetItem(i, stack);
                ClearSlot(stack);
                return true;
            }

            return false;
        }

        static void ClearSlot(ItemStack stack)
        {
            stack.Set(ItemValue.None.Clone(), 0);
        }

        static List<BoxTarget> FindBoxes(
            World world,
            EntityPlayer player,
            PlatformUserIdentifierAbs userId,
            QuickStackResult result,
            ref int skippedBusy)
        {
            var boxes = new List<BoxTarget>();
            float radius = result.RadiusMeters;
            float radiusSq = radius * radius;
            int chunkRadius = Mathf.CeilToInt(radius / 16f) + 1;
            Vector2i center = World.toChunkXZ(player.position);

            for (int cx = center.x - chunkRadius; cx <= center.x + chunkRadius; cx++)
            {
                for (int cz = center.y - chunkRadius; cz <= center.y + chunkRadius; cz++)
                {
                    Chunk chunk = world.GetChunkSync(cx, cz) as Chunk;
                    if (chunk == null)
                    {
                        continue;
                    }

                    DictionaryList<Vector3i, TileEntity> tiles = chunk.GetTileEntities();
                    if (tiles?.list == null)
                    {
                        continue;
                    }

                    for (int i = 0; i < tiles.list.Count; i++)
                    {
                        TileEntity tile = tiles.list[i];
                        TEFeatureStorage storage;
                        if (tile == null || tile.IsRemoving ||
                            !tile.TryGetSelfOrFeature(out storage) ||
                            storage.ItemGrid == null ||
                            !storage.ItemGrid.PlayerOwned)
                        {
                            continue;
                        }

                        float distanceSq = (tile.ToWorldCenterPos() - player.position).sqrMagnitude;
                        if (distanceSq > radiusSq)
                        {
                            continue;
                        }

                        if (tile.IsUserAccessing() || LockManager.Instance.IsLockedServer(storage, StorageChannel))
                        {
                            skippedBusy++;
                            continue;
                        }

                        if (!CanUseBox(tile, userId))
                        {
                            continue;
                        }

                        boxes.Add(new BoxTarget(storage, null, distanceSq));
                    }
                }
            }

            boxes.Sort((left, right) => left.DistanceSq.CompareTo(right.DistanceSq));
            return boxes;
        }

        static bool CanUseBox(TileEntity tile, PlatformUserIdentifierAbs userId)
        {
            TEFeatureLockable lockable;
            if (!tile.TryGetSelfOrFeature(out lockable) || lockable == null || !lockable.IsLocked())
            {
                return true;
            }

            return userId != null && lockable.IsUserAllowed(userId);
        }

        static EntityVehicle FindVehicle(
            World world,
            EntityPlayer player,
            PlatformUserIdentifierAbs userId,
            int radius,
            ref bool anyOwned)
        {
            float radiusSq = radius * radius;
            var found = new List<Entity>();
            world.GetEntitiesInBounds(
                typeof(EntityVehicle),
                new Bounds(player.position, Vector3.one * (radius * 2f)),
                found);

            EntityVehicle nearest = null;
            float nearestSq = float.MaxValue;
            for (int i = 0; i < found.Count; i++)
            {
                EntityVehicle vehicle = found[i] as EntityVehicle;
                if (vehicle == null || vehicle.IsDead() || vehicle.bag == null || vehicle.GetVehicle() == null)
                {
                    continue;
                }

                float distanceSq = (vehicle.position - player.position).sqrMagnitude;
                if (distanceSq > radiusSq)
                {
                    continue;
                }

                // IsOwner is true for an unowned vehicle. Require a real owner id.
                PlatformUserIdentifierAbs owner = vehicle.GetOwner();
                if (owner == null || userId == null || !owner.Equals(userId))
                {
                    continue;
                }

                anyOwned = true;
                if (vehicle.HasDriver ||
                    LockManager.Instance.IsLockedServer(vehicle, StorageChannel) ||
                    LockManager.Instance.IsLockedServer(vehicle, CollectChannel))
                {
                    continue;
                }

                if (distanceSq < nearestSq)
                {
                    nearest = vehicle;
                    nearestSq = distanceSq;
                }
            }

            return nearest;
        }

        static bool TryHold(ILockTarget target, ushort channel)
        {
            if (target == null)
            {
                return false;
            }

            if (LockManager.Instance.IsLockedServer(target, channel))
            {
                return false;
            }

            return HeldTargets.Add(target);
        }

        static void Release(List<ILockTarget> held)
        {
            for (int i = 0; i < held.Count; i++)
            {
                HeldTargets.Remove(held[i]);
            }
        }

        sealed class BoxTarget
        {
            public BoxTarget(TEFeatureStorage storage, EntityVehicle vehicle, float distanceSq)
            {
                Storage = storage;
                Vehicle = vehicle;
                DistanceSq = distanceSq;
            }

            public TEFeatureStorage Storage { get; }

            public EntityVehicle Vehicle { get; }

            public float DistanceSq { get; }
        }
    }
}
