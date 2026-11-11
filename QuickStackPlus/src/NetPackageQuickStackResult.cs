using System.Collections.Generic;
using System.IO;
using UnityEngine.Scripting;

namespace QuickStackPlus
{
    [Preserve]
    public sealed class NetPackageQuickStackResult : NetPackage
    {
        int playerEntityId;
        QuickStackResult result = new QuickStackResult();

        public override NetPackageDirection PackageDirection => NetPackageDirection.ToClient;

        public NetPackageQuickStackResult Setup(int entityId, QuickStackResult stackResult)
        {
            playerEntityId = entityId;
            result = stackResult ?? new QuickStackResult();
            return this;
        }

        public override void read(PooledBinaryReader reader)
        {
            playerEntityId = reader.ReadInt32();
            var stackResult = new QuickStackResult
            {
                Mode = (QuickStackMode)reader.ReadByte(),
                Outcome = (QuickStackOutcome)reader.ReadByte(),
                MovedItemCount = reader.ReadInt32(),
                ContainerCount = reader.ReadInt32(),
                RadiusMeters = reader.ReadInt32()
            };
            int count = reader.ReadInt32();
            for (int i = 0; i < count; i++)
            {
                int index = reader.ReadInt32();
                ItemStack stack = new ItemStack();
                stack.Read(reader);
                stackResult.Slots.Add(new SlotChange(index, stack));
            }

            result = stackResult;
        }

        public override void write(PooledBinaryWriter writer)
        {
            base.write(writer);
            BinaryWriter binaryWriter = writer;
            binaryWriter.Write(playerEntityId);
            binaryWriter.Write((byte)result.Mode);
            binaryWriter.Write((byte)result.Outcome);
            binaryWriter.Write(result.MovedItemCount);
            binaryWriter.Write(result.ContainerCount);
            binaryWriter.Write(result.RadiusMeters);
            List<SlotChange> slots = result.Slots;
            binaryWriter.Write(slots.Count);
            for (int i = 0; i < slots.Count; i++)
            {
                binaryWriter.Write(slots[i].Index);
                ItemStack stack = slots[i].Stack ?? ItemStack.Empty.Clone();
                stack.Write(writer);
            }
        }

        public override void ProcessPackage(World world, GameManager callbacks)
        {
            ConnectionManager connection = SingletonMonoBehaviour<ConnectionManager>.Instance;
            if (world == null || result == null || connection == null || connection.IsServer)
            {
                return;
            }

            EntityPlayerLocal player = world.GetPrimaryPlayer();
            if (player == null || player.entityId != playerEntityId)
            {
                return;
            }

            QuickStackClient.ApplyResult(result);
        }
    }
}
