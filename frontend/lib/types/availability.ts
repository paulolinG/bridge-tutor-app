export interface AvailabilityWindow {
  day_of_week: number;
  start_minute: number;
  end_minute: number;
}

export interface Availability {
  windows: AvailabilityWindow[];
  daily_cap_minutes: number | null;
  weekly_cap_minutes: number | null;
}

export interface UpdateAvailabilityRequest {
  windows: AvailabilityWindow[];
  daily_cap_minutes: number;
  weekly_cap_minutes: number;
}
