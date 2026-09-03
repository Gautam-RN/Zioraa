const tabCache = {};
let currentTabUrl = "";


/* =========================================
   LOAD TAB
========================================= */

async function loadTab(url) {

    currentTabUrl = url;

    document.querySelectorAll(".sidebar button").forEach(button => {
        button.classList.toggle("active", button.getAttribute("onclick")?.includes(url));
    });

    const content = document.getElementById("content-area");

    // CACHE
    if (tabCache[url]) {

        content.innerHTML = tabCache[url];

        refreshTab(url);

        return;
    }

    content.innerHTML = `
        <div class="loader">
            Loading...
        </div>
    `;

    try {

        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(`Tab request failed: ${response.status}`);
        }

        const html = await response.text();

        tabCache[url] = html;

        content.innerHTML = html;

    }

    catch(error) {

        console.error(error);

    }
}


/* =========================================
   REFRESH TAB
========================================= */

async function refreshTab(url) {

    try {

        const response = await fetch(url);

        const html = await response.text();

        tabCache[url] = html;

        if (currentTabUrl === url) {

            document.getElementById("content-area").innerHTML = html;

        }

    }

    catch(error) {

        console.error(error);

    }
}


/* =========================================
   SIDEBAR
========================================= */

function toggleSidebar() {

    document
        .querySelector(".sidebar")
        .classList
        .toggle("active");

    document
        .querySelector(".overlay")
        .classList
        .toggle("active");
}


document.querySelectorAll(".sidebar button")
.forEach(btn => {

    btn.addEventListener("click", () => {

        document
            .querySelector(".sidebar")
            .classList
            .remove("active");

        document
            .querySelector(".overlay")
            .classList
            .remove("active");

    });

});


/* =========================================
   AJAX FORMS
========================================= */

document.addEventListener("submit", async function(e) {

    const form = e.target;

    // ONLY AJAX FORMS
    if (!form.classList.contains("ajax-form")) {
        return;
    }

    e.preventDefault();

    try {

        const response = await fetch(form.action, {
            method: form.method,
            body: new FormData(form)
        });

        const contentType =
            response.headers.get("content-type");



        /* =========================================
           HTML RESPONSE
        ========================================= */

        if (
            contentType &&
            contentType.includes("text/html")
        ) {

            const html = await response.text();

            document.getElementById(
                "content-area"
            ).innerHTML = html;

            return;
        }



        /* =========================================
           JSON RESPONSE
        ========================================= */

        const data = await response.json();

        alert(data.message);

        // REFRESH CURRENT TAB
        loadTab(currentTabUrl);

    }

    catch(error) {

        console.error(error);

        alert("Something went wrong");

    }

});