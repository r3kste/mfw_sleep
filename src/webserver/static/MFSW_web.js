document.addEventListener("DOMContentLoaded", () => {
    console.log("MFSW_web.js loaded");

    let isListening = false;
    let isAlarmPlaying = false;

    document.getElementById("startButton").addEventListener("click", () => {
        const startButton = document.getElementById("startButton");

        if (!isListening) {
            // Start listening
            isListening = true;
            startButton.textContent = "Listening... Click again to stop";

            fetch("http://localhost:8080/start")
                .then(response => response.json())
                .then(data => {
                    if (data.message === "El Psy Congroo") {
                        triggerAlarm();
                    }
                })
                .catch(error => console.error("Error:", error));
        } else {
            // Show custom confirmation modal
            showConfirmModal(() => {
                // User confirmed
                isListening = false;
                startButton.textContent = "Start";
                alert("Stopped listening.");
            });
        }
    });

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

