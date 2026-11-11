using System.Reflection;
using HarmonyLib;
using UnityEngine.Scripting;

namespace QuickStackPlus
{
    [Preserve]
    public sealed class QuickStackPlusApi : IModApi
    {
        public void InitMod(Mod modInstance)
        {
            QuickStackConfig.Load(modInstance?.Path);
            var harmony = new Harmony("com.cyberpoke.quickstackplus");
            harmony.PatchAll(Assembly.GetExecutingAssembly());
            ModEvents.UnityUpdate.RegisterHandler(QuickStackClient.OnUnityUpdate);
            Log.Out("[QuickStackPlus] Loaded for 7 Days to Die V3.4. Radius " +
                QuickStackConfig.RadiusMeters + " m.");
        }
    }
}
