using HarmonyLib;
using UnityEngine.Scripting;

namespace QuickStackPlus
{
    [Preserve]
    [HarmonyPatch(typeof(XUiC_BackpackWindow), nameof(XUiC_BackpackWindow.Init))]
    public static class BackpackWindowPatch
    {
        static void Postfix(XUiC_BackpackWindow __instance)
        {
            Bind(__instance, "btnQuickStackNearby", QuickStackMode.Nearby, "qspNearbyTip", QuickStackConfig.HotkeyNearby);
            Bind(__instance, "btnQuickStackVehicle", QuickStackMode.VehicleMatch, "qspVehicleTip", QuickStackConfig.HotkeyVehicleMatch);
            Bind(__instance, "btnQuickStackVehicleAll", QuickStackMode.VehicleAll, "qspVehicleAllTip", QuickStackConfig.HotkeyVehicleAll);
        }

        static void Bind(
            XUiController window,
            string id,
            QuickStackMode mode,
            string tooltipKey,
            UnityEngine.KeyCode hotkey)
        {
            XUiController button = window.GetChildById(id);
            if (button == null)
            {
                Log.Warning("[QuickStackPlus] Backpack button '" + id + "' was not found. Use qsp in the console.");
                return;
            }

            if (button.ViewComponent != null)
            {
                string tip = Localization.Get(tooltipKey);
                button.ViewComponent.ToolTip = QuickStackMessages.WithHotkey(tip, hotkey);
            }

            button.OnPress -= OnNearby;
            button.OnPress -= OnVehicleMatch;
            button.OnPress -= OnVehicleAll;
            if (mode == QuickStackMode.Nearby)
            {
                button.OnPress += OnNearby;
            }
            else if (mode == QuickStackMode.VehicleMatch)
            {
                button.OnPress += OnVehicleMatch;
            }
            else
            {
                button.OnPress += OnVehicleAll;
            }
        }

        static void OnNearby(XUiController sender, int mouseButton)
        {
            QuickStackClient.NotifyNearbyPressed();
        }

        static void OnVehicleMatch(XUiController sender, int mouseButton)
        {
            QuickStackClient.Request(QuickStackMode.VehicleMatch);
        }

        static void OnVehicleAll(XUiController sender, int mouseButton)
        {
            QuickStackClient.Request(QuickStackMode.VehicleAll);
        }
    }
}
