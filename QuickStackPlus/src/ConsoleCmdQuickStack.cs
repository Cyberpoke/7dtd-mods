using System.Collections.Generic;
using Platform;
using UnityEngine.Scripting;

namespace QuickStackPlus
{
    [Preserve]
    public sealed class ConsoleCmdQuickStack : ConsoleCmdAbstract
    {
        public override bool IsExecuteOnClient => false;

        public override int DefaultPermissionLevel => 0;

        public override string[] getCommands()
        {
            return new[] { "qsp", "quickstack" };
        }

        public override string getDescription()
        {
            return "Quick-stack the backpack into nearby boxes or your own vehicle.";
        }

        public override string getHelp()
        {
            return "Usage:\n" +
                "  qsp nearby    Top up matching stacks in your boxes within range\n" +
                "  qsp vehicle   Top up matching stacks in your own vehicle\n" +
                "  qsp all       Move every unlocked backpack slot into your vehicle\n" +
                "Locked backpack slots and the toolbelt are left alone. The server clamps range to 20 m.";
        }

        public override void Execute(List<string> _params, CommandSenderInfo _senderInfo)
        {
            QuickStackMode mode;
            if (_params == null || _params.Count != 1 || !TryParse(_params[0], out mode))
            {
                SdtdConsole.Instance.Output(GetHelp());
                return;
            }

            World world = GameManager.Instance?.World;
            if (world == null)
            {
                SdtdConsole.Instance.Output("No world is running.");
                return;
            }

            ClientInfo client = _senderInfo.RemoteClientInfo;
            EntityPlayer player;
            PlatformUserIdentifierAbs userId;
            if (client != null)
            {
                player = world.GetEntity(client.entityId) as EntityPlayer;
                userId = client.InternalId;
            }
            else
            {
                player = world.GetPrimaryPlayer();
                ClientInfo localClient = SingletonMonoBehaviour<ConnectionManager>.Instance?.Clients?
                    .ForEntityId(player != null ? player.entityId : -1);
                userId = localClient?.InternalId ?? PlatformManager.InternalLocalUserIdentifier;
                client = localClient;
            }

            if (player == null)
            {
                SdtdConsole.Instance.Output("No player is available for this command.");
                return;
            }

            QuickStackResult result = QuickStackService.Run(world, player, client, userId, mode);
            string message = QuickStackMessages.Format(result);
            SdtdConsole.Instance.Output(message);
            if (player is EntityPlayerLocal local)
            {
                QuickStackMessages.Show(local, result);
                return;
            }

            SingletonMonoBehaviour<ConnectionManager>.Instance.SendPackage(
                NetPackageManager.GetPackage<NetPackageQuickStackResult>().Setup(player.entityId, result),
                false,
                player.entityId);
        }

        static bool TryParse(string text, out QuickStackMode mode)
        {
            switch ((text ?? string.Empty).Trim().ToLowerInvariant())
            {
                case "nearby":
                case "boxes":
                    mode = QuickStackMode.Nearby;
                    return true;
                case "vehicle":
                case "match":
                    mode = QuickStackMode.VehicleMatch;
                    return true;
                case "all":
                case "everything":
                    mode = QuickStackMode.VehicleAll;
                    return true;
                default:
                    mode = QuickStackMode.Nearby;
                    return false;
            }
        }
    }
}
