namespace QuickStackPlus
{
    public static class QuickStackMessages
    {
        public static string Format(QuickStackResult result)
        {
            if (result == null)
            {
                return "Quick stack could not be completed";
            }

            int radius = result.RadiusMeters;
            switch (result.Outcome)
            {
                case QuickStackOutcome.Moved:
                    if (result.Mode == QuickStackMode.Nearby)
                    {
                        return "Stacked " + Noun(result.MovedItemCount, "item") + " into " +
                            Noun(result.ContainerCount, "box");
                    }

                    if (result.Mode == QuickStackMode.NearbyType)
                    {
                        return "Moved " + Noun(result.MovedItemCount, "item") + " into " +
                            Noun(result.ContainerCount, "box");
                    }

                    if (result.Mode == QuickStackMode.VehicleMatch)
                    {
                        return "Stacked " + Noun(result.MovedItemCount, "item") + " into your vehicle";
                    }

                    return "Moved " + Noun(result.MovedItemCount, "item") + " into your vehicle";
                case QuickStackOutcome.NoStorage:
                    return "No accessible storage within " + radius + "m";
                case QuickStackOutcome.Busy:
                    return "Nearby boxes are in use";
                case QuickStackOutcome.NoMatch:
                    if (result.Mode == QuickStackMode.Nearby || result.Mode == QuickStackMode.NearbyType)
                    {
                        return "No matching stacks in nearby boxes";
                    }

                    return "No matching stacks in your vehicle";
                case QuickStackOutcome.NoVehicle:
                    return "No owned vehicle within " + radius + "m";
                case QuickStackOutcome.VehicleBusy:
                    return "Your vehicle is in use";
                default:
                    if (result.Mode == QuickStackMode.NearbyType)
                    {
                        return "No room in nearby boxes";
                    }

                    return "No room in your vehicle";
            }
        }

        public static void Show(EntityPlayerLocal player, QuickStackResult result)
        {
            if (player != null)
            {
                GameManager.ShowTooltip(player, Format(result), false, false, 3f);
            }
        }

        public static string WithHotkey(string tip, UnityEngine.KeyCode key)
        {
            if (key == UnityEngine.KeyCode.None)
            {
                return tip;
            }

            return tip + " [" + key + "]";
        }

        private static string Noun(int count, string word)
        {
            if (count == 1)
            {
                return "1 " + word;
            }

            return count + " " + word + "s";
        }
    }
}
