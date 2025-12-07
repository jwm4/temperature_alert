# Freeze Alert System Walkthrough

Your freeze alert system is set up and running on your PC!

## 1. How to Receive Alerts on Your iPhone
1.  Install the **ntfy** app from the App Store (it's free and requires no account).
2.  Open the app and tap the **+** button to subscribe to a topic.
3.  Enter the topic name: `bill-freeze-alerts-13459`
4.  Tap **Subscribe**.

You will now receive a notification whenever the script detects a freeze (below 20°F) for the upcoming night.

## 2. How It Works
*   **Schedule**: The script runs automatically every day at **8:15 PM** on your PC.
*   **Logic**: It checks the overnight forecast for Sharon Springs, NY. If the temperature drops below **20°F**, it sends an alert.
*   **Requirements**: Your PC must be on or in sleep mode (it is configured to wake up to run the task).

## 3. Testing the System
To verify it works right now:
1.  Open **Task Scheduler** on Windows.
2.  Find the task named `TemperatureAlertSystem`.
3.  Right-click it and select **Run**.
4.  If the temperature is below 20°F tonight, you will get an alert.
    *   *Note: Since the current forecast is likely above 20°F, you might not get an alert. To force a test alert, you can edit the `freeze_alert.py` file and change `THRESHOLD_F` to `100` temporarily.*

## 4. Troubleshooting
*   **No Alert?** Check if your PC was on at 4:00 PM.
*   **Error?** You can view the "Last Run Result" in Task Scheduler.
