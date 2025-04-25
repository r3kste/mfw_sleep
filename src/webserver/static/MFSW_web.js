document.addEventListener("DOMContentLoaded", () => {
    console.log("MFSW_web.js loaded");

    let isAlarmPlaying = false;

    // Camera Start Button
    document.getElementById("cameraStartButton").addEventListener("click", () => {
        fetch("http://localhost:8080/camera/start")
            .then(response => {
                if (response.ok) {
                    alert("Camera started!");
                } else {
                    alert("Failed to start the camera.");
                }
            })
            .catch(error => console.error("Error:", error));
    });

    // Camera Stop Button
    document.getElementById("cameraStopButton").addEventListener("click", () => {
        fetch("http://localhost:8080/camera/stop")
            .then(response => {
                if (response.ok) {
                    alert("Camera stopped!");
                } else {
                    alert("Failed to stop the camera.");
                }
            })
            .catch(error => console.error("Error:", error));
    }
    );

    document.getElementById("alarmButton").addEventListener("click", () => {
        if (isAlarmPlaying) {
            stopAlarm();
        }
    });

    document.getElementById("triggerAlarmButton").addEventListener("click", () => {
        if (!isAlarmPlaying) {
            triggerAlarm();
        }
    });

    function triggerAlarm() {
        isAlarmPlaying = true;

        // Update button states
        document.getElementById("alarmButton").textContent = "Stop Alarm";
        document.getElementById("alarmButton").disabled = false;
        document.getElementById("triggerAlarmButton").disabled = true;

        fetch("http://localhost:8080/alarm/start")
            .then(response => {
                if (response.ok) {
                    alert("Alarm is ringing!");
                }
            })
            .catch(error => console.error("Error:", error));
    }

    function stopAlarm() {
        isAlarmPlaying = false;

        // Update button states
        document.getElementById("alarmButton").textContent = "Alarm";
        document.getElementById("alarmButton").disabled = true;
        document.getElementById("triggerAlarmButton").disabled = false;

        fetch("http://localhost:8080/alarm/stop")
            .then(response => {
                if (response.ok) {
                    alert("Alarm stopped.");
                }
            })
            .catch(error => console.error("Error:", error));
    }

    function showConfirmModal(onConfirm) {
        const modal = document.getElementById("confirmModal");
        modal.style.display = "block";

        document.getElementById("confirmYes").onclick = () => {
            modal.style.display = "none";
            onConfirm(); // Execute the callback function
        };

        document.getElementById("confirmNo").onclick = () => {
            modal.style.display = "none";
        };
    }
});

