const blockchainView = document.getElementById("chainView");
const blockForm = document.getElementById("addBlockForm");
const messageBox = document.getElementById("formMsg");
let blockchain = [];


function createBlockCard(block) {
    /**
     * Create a block card.
     * 
     * @param {Object} block - The block to create a card for.
     * @returns {Object} The created block card.
     */
    const cardWrapper = document.createElement("div");
    cardWrapper.className = "block-card p-3";
    cardWrapper.innerHTML = `
    <h6 class="fw-semibold mb-1">Block #${block.header.block_num}</h6>
    <div class="hash mb-1"><b>Prev:</b> ${block.header.prev_block_hash}</div>
    <div class="hash mb-1"><b>Merkle:</b> ${block.header.merkle_root_hash}</div>
    <div class="small">
        <b>Time:</b> ${new Date(block.header.timestamp_ms).toLocaleString()}<br>
        <b>Diff:</b> ${block.header.difficulty}  
        <b>Nonce:</b> ${block.header.nonce}
    </div>
    <div class="tx-list collapse"></div>`;

    cardWrapper.onclick = () => {
    const transactionList = cardWrapper.querySelector(".tx-list");
    if (transactionList.classList.contains("show")) {
        transactionList.classList.remove("show");
        transactionList.innerHTML = "";
    } else {
        transactionList.classList.add("show");
        transactionList.innerHTML = block.transactions.map(transaction =>
        `<div class="tx">• ${transaction.sender} → ${transaction.recipient} : ${transaction.artwork_id}</div>`
        ).join("");
    }
    };
    return cardWrapper;
}

function renderBlockchain() {
    /**
     * Render the blockchain.
     */
    blockchainView.innerHTML = "";
    blockchain.forEach(block => blockchainView.appendChild(createBlockCard(block)));
}


async function fetchBlockchain() {
    /**
     * Fetch the blockchain.
     */
    const response = await fetch("/api/blocks");
    blockchain = await response.json();
    renderBlockchain();
}


blockForm.addEventListener("submit", async event => {
    /**
     * Submit the block form.
     */
    event.preventDefault();
    messageBox.classList.add("d-none");

    const formData = Object.fromEntries(new FormData(blockForm).entries());
    const response = await fetch("/api/block", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData)
    });

    if (response.ok) {
        blockForm.reset();
        fetchBlockchain();
    } else {
        const { error } = await response.json();
      
        messageBox.textContent = `Cannot add this block — ${error}.`;
        messageBox.classList.remove("d-none");
        messageBox.classList.add("msg-animate");
      
        const panel = document.querySelector(".live-card");
        panel.classList.add("card-reject");
        setTimeout(() => panel.classList.remove("card-reject"), 650);
      
        setTimeout(()=>{
            messageBox.classList.add("d-none");
            messageBox.classList.remove("msg-animate");
        }, 3000);
    }
});

let eventSource;
let retryCount = 0;

function openEventStream() {
    /**
     * Open the event stream.
     */
    eventSource = new EventSource("/stream");

    eventSource.onmessage = event => {
    retryCount = 0;
    const payload = JSON.parse(event.data);

    if (payload.type === "INIT") {
        blockchain = payload.chain;
        renderBlockchain();
    } else if (payload.type === "BLOCK_ADDED") {
        blockchain.push(payload.block);
        const newCard = createBlockCard(payload.block);
        newCard.classList.add("block-pulse");
        blockchainView.appendChild(newCard);
        newCard.scrollIntoView({ behavior: "smooth" });
    }
    };

    eventSource.onerror = () => {
    eventSource.close();
    retryCount = Math.min(retryCount + 1, 6);
    setTimeout(openEventStream, 2 ** retryCount * 1000);
    };
}

openEventStream();

setInterval(() => {
  if (eventSource.readyState === EventSource.CLOSED) {
    fetchBlockchain();
  }
}, 5000);

fetchBlockchain();
