using System.Collections.Generic;

namespace QuickStackPlus
{
    public sealed class SlotChange
    {
        public SlotChange(int index, ItemStack stack)
        {
            Index = index;
            Stack = stack;
        }

        public int Index { get; }

        public ItemStack Stack { get; }
    }

    public sealed class QuickStackResult
    {
        public QuickStackMode Mode { get; set; }

        public QuickStackOutcome Outcome { get; set; }

        public int MovedItemCount { get; set; }

        public int ContainerCount { get; set; }

        public int RadiusMeters { get; set; }

        public List<SlotChange> Slots { get; } = new List<SlotChange>();
    }
}
