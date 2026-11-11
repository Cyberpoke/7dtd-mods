using System;
using System.Globalization;
using System.IO;
using System.Xml.Linq;
using UnityEngine;

namespace QuickStackPlus
{
    public static class QuickStackConfig
    {
        public const int MaxRadius = 20;

        public static int RadiusMeters { get; private set; } = MaxRadius;

        public static KeyCode HotkeyNearby { get; private set; } = KeyCode.Keypad7;

        public static KeyCode HotkeyVehicleMatch { get; private set; } = KeyCode.Keypad8;

        public static KeyCode HotkeyVehicleAll { get; private set; } = KeyCode.Keypad9;

        public static void Load(string modPath)
        {
            RadiusMeters = MaxRadius;
            HotkeyNearby = KeyCode.Keypad7;
            HotkeyVehicleMatch = KeyCode.Keypad8;
            HotkeyVehicleAll = KeyCode.Keypad9;

            string path = Path.Combine(modPath ?? string.Empty, "settings.xml");
            if (!File.Exists(path))
            {
                Log.Out("[QuickStackPlus] No settings.xml. Range " + RadiusMeters + " m.");
                return;
            }

            try
            {
                XDocument document = XDocument.Load(path);
                XElement root = document.Root;
                if (root == null)
                {
                    return;
                }

                RadiusMeters = ClampRadius(ReadInt(root, "RangeMeters", MaxRadius));
                HotkeyNearby = ReadKey(root, "HotkeyNearby", HotkeyNearby);
                HotkeyVehicleMatch = ReadKey(root, "HotkeyVehicleMatch", HotkeyVehicleMatch);
                HotkeyVehicleAll = ReadKey(root, "HotkeyVehicleAll", HotkeyVehicleAll);
            }
            catch (Exception e)
            {
                Log.Warning("[QuickStackPlus] Could not read settings.xml. Using defaults.");
                Log.Exception(e);
            }

            Log.Out("[QuickStackPlus] Range " + RadiusMeters + " m (clamped to " + MaxRadius + ").");
        }

        public static int ClampRadius(int radius)
        {
            if (radius < 1)
            {
                return 1;
            }

            if (radius > MaxRadius)
            {
                return MaxRadius;
            }

            return radius;
        }

        private static int ReadInt(XElement root, string name, int fallback)
        {
            XElement element = root.Element(name);
            if (element == null)
            {
                return fallback;
            }

            int value;
            if (int.TryParse(element.Value.Trim(), NumberStyles.Integer, CultureInfo.InvariantCulture, out value))
            {
                return value;
            }

            Log.Warning("[QuickStackPlus] " + name + " is not a number. Using " + fallback + ".");
            return fallback;
        }

        private static KeyCode ReadKey(XElement root, string name, KeyCode fallback)
        {
            XElement element = root.Element(name);
            if (element == null)
            {
                return fallback;
            }

            string text = element.Value.Trim();
            if (text.Length == 0 || text.Equals("None", StringComparison.OrdinalIgnoreCase))
            {
                return KeyCode.None;
            }

            KeyCode key;
            if (Enum.TryParse(text, true, out key))
            {
                return key;
            }

            Log.Warning("[QuickStackPlus] Unknown KeyCode '" + text + "' for " + name + ".");
            return KeyCode.None;
        }
    }
}
