using Platform;
using UnityEngine;

namespace QuickStackPlus
{
    public static class QuickStackClient
    {
        public const float DoubleClickSeconds = 0.4f;

        const float CooldownSeconds = 0.4f;

        static float nextAllowedTime;
        static float lastNearbyClick = -1f;

        public static void NotifyNearbyPressed()
        {
            float now = Time.unscaledTime;
            if (lastNearbyClick >= 0f && now - lastNearbyClick <= DoubleClickSeconds)
            {
                lastNearbyClick = -1f;
                Request(QuickStackMode.NearbyType, true);
                return;
            }

            if (Request(QuickStackMode.Nearby, false))
            {
                lastNearbyClick = Time.unscaledTime;
            }
        }

        public static void Request(QuickStackMode mode)
        {
            Request(mode, false);
        }

        static bool Request(QuickStackMode mode, bool ignoreCooldown)
        {
            if (!ignoreCooldown && Time.unscaledTime < nextAllowedTime)
            {
                return false;
            }

            World world = GameManager.Instance?.World;
            EntityPlayerLocal player = world?.GetPrimaryPlayer();
            if (world == null || player == null || player.IsDead())
            {
                return false;
            }

            if (mode == QuickStackMode.NearbyType)
            {
                lastNearbyClick = -1f;
            }

            nextAllowedTime = Time.unscaledTime + CooldownSeconds;
            ConnectionManager connection = SingletonMonoBehaviour<ConnectionManager>.Instance;
            if (connection == null)
            {
                QuickStackMessages.Show(player, Failed(mode));
                return true;
            }

            if (connection.IsServer)
            {
                ClientInfo client = connection.Clients?.ForEntityId(player.entityId);
                PlatformUserIdentifierAbs userId = client?.InternalId ?? PlatformManager.InternalLocalUserIdentifier;
                QuickStackResult result = QuickStackService.Run(world, player, client, userId, mode);
                QuickStackMessages.Show(player, result);
                return true;
            }

            connection.SendToServer(
                NetPackageManager.GetPackage<NetPackageQuickStackRequest>().Setup(player.entityId, mode));
            return true;
        }

        public static void ApplyResult(QuickStackResult result)
        {
            World world = GameManager.Instance?.World;
            EntityPlayerLocal player = world?.GetPrimaryPlayer();
            if (player?.bag == null || result == null)
            {
                return;
            }

            ItemStackGrid grid = player.bag.ItemGrid;
            for (int i = 0; i < result.Slots.Count; i++)
            {
                SlotChange change = result.Slots[i];
                if (change.Index < 0 || change.Index >= grid.Length)
                {
                    continue;
                }

                ItemStack incoming = change.Stack;
                if (incoming == null || incoming.IsEmpty())
                {
                    grid[change.Index].Set(ItemValue.None.Clone(), 0);
                }
                else
                {
                    grid[change.Index].Set(incoming.itemValue.Clone(), incoming.count);
                }
            }

            QuickStackMessages.Show(player, result);
            Log.Out("[QuickStackPlus] " + QuickStackMessages.Format(result));
        }

        public static void OnUnityUpdate(ref ModEvents.SUnityUpdateData _data)
        {
            if (GameManager.IsDedicatedServer)
            {
                return;
            }

            World world = GameManager.Instance?.World;
            EntityPlayerLocal player = world?.GetPrimaryPlayer();
            if (player == null || player.IsDead())
            {
                return;
            }

            LocalPlayerUI ui = LocalPlayerUI.GetUIForPrimaryPlayer();
            if (ui?.windowManager != null && ui.windowManager.IsInputActive())
            {
                return;
            }

            if (Pressed(QuickStackConfig.HotkeyNearby))
            {
                if (Input.GetKey(KeyCode.LeftShift) || Input.GetKey(KeyCode.RightShift))
                {
                    Request(QuickStackMode.NearbyType, true);
                }
                else
                {
                    Request(QuickStackMode.Nearby);
                }
            }
            else if (Pressed(QuickStackConfig.HotkeyVehicleMatch))
            {
                Request(QuickStackMode.VehicleMatch);
            }
            else if (Pressed(QuickStackConfig.HotkeyVehicleAll))
            {
                Request(QuickStackMode.VehicleAll);
            }
        }

        static bool Pressed(KeyCode key)
        {
            return key != KeyCode.None && Input.GetKeyDown(key);
        }

        static QuickStackResult Failed(QuickStackMode mode)
        {
            return new QuickStackResult
            {
                Mode = mode,
                Outcome = mode == QuickStackMode.VehicleMatch || mode == QuickStackMode.VehicleAll
                    ? QuickStackOutcome.NoVehicle
                    : QuickStackOutcome.NoStorage,
                RadiusMeters = QuickStackConfig.RadiusMeters
            };
        }
    }
}
