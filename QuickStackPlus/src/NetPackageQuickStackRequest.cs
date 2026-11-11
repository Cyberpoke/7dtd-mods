using System.IO;
using UnityEngine.Scripting;

namespace QuickStackPlus
{
    [Preserve]
    public sealed class NetPackageQuickStackRequest : NetPackage
    {
        int playerEntityId;
        QuickStackMode mode;

        public override NetPackageDirection PackageDirection => NetPackageDirection.ToServer;

        public NetPackageQuickStackRequest Setup(int entityId, QuickStackMode stackMode)
        {
            playerEntityId = entityId;
            mode = stackMode;
            return this;
        }

        public override void read(PooledBinaryReader reader)
        {
            playerEntityId = reader.ReadInt32();
            mode = (QuickStackMode)reader.ReadByte();
        }

        public override void write(PooledBinaryWriter writer)
        {
            base.write(writer);
            BinaryWriter binaryWriter = writer;
            binaryWriter.Write(playerEntityId);
            binaryWriter.Write((byte)mode);
        }

        public override void ProcessPackage(World world, GameManager callbacks)
        {
            ConnectionManager connection = SingletonMonoBehaviour<ConnectionManager>.Instance;
            if (world == null || connection == null || !connection.IsServer || Sender == null)
            {
                return;
            }

            if (!IsKnown(mode) || !ValidEntityIdForSender(playerEntityId))
            {
                return;
            }

            EntityPlayer player = world.GetEntity(playerEntityId) as EntityPlayer;
            if (player == null)
            {
                return;
            }

            QuickStackResult result = QuickStackService.Run(world, player, Sender, Sender.InternalId, mode);
            if (player is EntityPlayerLocal local)
            {
                QuickStackMessages.Show(local, result);
                return;
            }

            connection.SendPackage(
                NetPackageManager.GetPackage<NetPackageQuickStackResult>().Setup(playerEntityId, result),
                false,
                playerEntityId);
        }

        static bool IsKnown(QuickStackMode stackMode)
        {
            return stackMode == QuickStackMode.Nearby ||
                stackMode == QuickStackMode.VehicleMatch ||
                stackMode == QuickStackMode.VehicleAll;
        }
    }
}
