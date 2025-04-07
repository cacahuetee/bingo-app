const socket = io();

// Unirse a una sala (si hay un ID de sala definido en el HTML)
const roomInput = document.getElementById("bingoId");
const joinButton = document.querySelector("a[href*='multijugador']");

if (roomInput && joinButton) {
    joinButton.addEventListener("click", (e) => {
        const roomCode = roomInput.value;
        if (roomCode.trim() !== "") {
            socket.emit("join_game", { room: roomCode });
            alert(`🎉 Te has unido a la sala ${roomCode}`);
        }
    });
}

// Escuchar número nuevo del servidor
socket.on("new_number", (data) => {
    console.log("Nuevo número:", data.number);
    // Aquí podrías marcar el número en el cartón visualmente
    const numberDisplay = document.getElementById("numero-actual");
    if (numberDisplay) {
        numberDisplay.textContent = `🎱 Número actual: ${data.number}`;
    }
});

// Escuchar mensaje de otros usuarios
socket.on("user_joined", (data) => {
    console.log(data.msg);
});
