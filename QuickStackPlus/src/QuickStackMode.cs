namespace QuickStackPlus
{
    public enum QuickStackMode : byte
    {
        Nearby = 0,
        VehicleMatch = 1,
        VehicleAll = 2
    }

    public enum QuickStackOutcome : byte
    {
        Moved = 0,
        NoStorage = 1,
        Busy = 2,
        NoMatch = 3,
        NoVehicle = 4,
        VehicleBusy = 5,
        NoRoom = 6
    }
}
