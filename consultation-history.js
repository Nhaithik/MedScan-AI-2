import {
  auth,
  db,
  getDocs,
  updateDoc,
  deleteDoc,
  doc,
  collection,
  onAuthStateChanged
} from "./firebase.js";


const tableBody =
  document.getElementById("tableBody");

const totalConsultations =
  document.getElementById("totalConsultations");

const searchInput =
  document.getElementById("searchInput");

const typeFilter =
  document.getElementById("typeFilter");

const statusFilter =
  document.getElementById("statusFilter");

const resetBtn =
  document.getElementById("resetBtn");

const resultsNote =
  document.querySelector(".results-note");


let allReports = [];
let filteredReports = [];

let currentPage = 1;
const pageSize = 5;


/* =========================================================
   HTML ESCAPE
   ========================================================= */

function escapeHtml(value) {

  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");

}


/* =========================================================
   REPORT DATE
   ========================================================= */

function getReportDate(report) {

  return report.createdAt?.toDate
    ? report.createdAt.toDate()
    : new Date(0);

}


/* =========================================================
   CONDITION
   ========================================================= */

function extractCondition(result) {

  if (!result) {
    return "AI Analysis";
  }

  const text = String(result);


  const match = text.match(
    /(?:Possible Condition|Condition)\s*[:\-]?\s*([^\n]+)/i
  );


  if (match?.[1]) {

    return match[1]
      .replace(/\*\*/g, "")
      .trim();

  }


  const line =
    text
      .split("\n")
      .map(value =>
        value
          .replace(/\*/g, "")
          .trim()
      )
      .find(Boolean);


  return line || "AI Analysis";

}


/* =========================================================
   PATIENT NAME
   ========================================================= */

function getPatientName(report) {

  const isAnimal =
    String(
      report.type || ""
    ).toLowerCase() === "animal";


  if (isAnimal) {

    return (
      report.breed ||
      report.animalType ||
      "Animal"
    );

  }


  return (
    report.consultationData?.Name ||
    report.consultationData?.name ||
    report.fullName ||
    "User"
  );

}


/* =========================================================
   LOAD CONSULTATIONS
   ========================================================= */

async function loadConsultations(uid) {

  try {

    console.log(
      "Loading consultations for:",
      uid
    );


    const snapshot =
      await getDocs(
        collection(
          db,
          "users",
          uid,
          "consultations"
        )
      );


    allReports = [];


    snapshot.forEach(
      (docSnapshot) => {

        allReports.push({

          id:
            docSnapshot.id,

          ...docSnapshot.data()

        });

      }
    );


    console.log(
      "Consultations loaded:",
      allReports.length
    );


    allReports.sort(
      (a, b) =>
        getReportDate(b) -
        getReportDate(a)
    );


    totalConsultations.textContent =
      allReports.length;


    currentPage = 1;

    applyFilters();


    /* =====================================================
       DASHBOARD → HISTORY → SPECIFIC REPORT
       ===================================================== */

    const selectedReportId =
      sessionStorage.getItem(
        "mediscan_selected_report_id"
      );


    if (selectedReportId) {

      const selectedReport =
        allReports.find(
          report =>
            report.id ===
            selectedReportId
        );


      if (selectedReport) {

        setTimeout(
          () => {

            viewReport(
              selectedReportId
            );

          },
          200
        );

      }


      sessionStorage.removeItem(
        "mediscan_selected_report_id"
      );

    }


  } catch (error) {

    console.error(
      "History Firestore error:",
      error
    );


    tableBody.innerHTML = `
      <tr>

        <td
          colspan="6"
          style="
            text-align:center;
            padding:50px;
            color:#e15b5b;
          "
        >

          Unable to load your
          consultation history.

          <br><br>

          ${escapeHtml(error.message)}

        </td>

      </tr>
    `;


    totalConsultations.textContent =
      "0";

    updateResultsNote(0);

  }

}


/* =========================================================
   FIREBASE AUTH
   ========================================================= */

onAuthStateChanged(
  auth,
  async (user) => {

    console.log(
      "HISTORY AUTH USER:",
      user
    );


    if (!user) {

      console.error(
        "NO FIREBASE USER ON HISTORY PAGE"
      );


      tableBody.innerHTML = `
        <tr>

          <td
            colspan="6"
            style="
              text-align:center;
              padding:50px;
              color:#5b6b8c;
            "
          >

            Please log in to view
            your consultation history.

          </td>

        </tr>
      `;


      totalConsultations.textContent =
        "0";


      updateResultsNote(0);


      return;

    }


    console.log(
      "HISTORY EMAIL:",
      user.email
    );


    console.log(
      "HISTORY UID:",
      user.uid
    );


    await loadConsultations(
      user.uid
    );

  }
);


/* =========================================================
   CREATE ROW
   ========================================================= */

function createRow(report) {

  const isAnimal =
    String(
      report.type || "Human"
    ).toLowerCase() ===
    "animal";


  const typeClass =
    isAnimal
      ? "animal"
      : "human";


  const date =
    getReportDate(report);


  const validDate =
    date.getTime() > 0;


  const dateText =
    validDate
      ? date.toLocaleDateString(
          "en-US",
          {
            year: "numeric",
            month: "short",
            day: "numeric"
          }
        )
      : "—";


  const timeText =
    validDate
      ? date.toLocaleTimeString(
          "en-US",
          {
            hour: "numeric",
            minute: "2-digit"
          }
        )
      : "";


  const patientName =
    getPatientName(report);


  const condition =
    extractCondition(
      report.aiResult
    );


  const status =
    String(
      report.status ||
      "Completed"
    );


  const statusClass =
    status.toLowerCase() ===
    "completed"
      ? "completed"
      : "progress";


  const reportId =
    escapeHtml(
      report.id
    );


  return `

    <tr>

      <td class="date-cell">

        <b>
          ${escapeHtml(dateText)}
        </b>

        <span>
          ${escapeHtml(timeText)}
        </span>

      </td>


      <td>

        <div class="patient-cell">

          <div class="p-avatar ${typeClass}">

            ${
              isAnimal
                ? "🐾"
                : "👤"
            }

          </div>


          <div>

            <b>
              ${escapeHtml(patientName)}
            </b>

            <span>
              ID:
              ${escapeHtml(
                report.id.slice(0, 8)
              )}
            </span>

          </div>

        </div>

      </td>


      <td>

        <span class="type-chip ${typeClass}">

          ${
            isAnimal
              ? "Animal"
              : "Human"
          }

        </span>

      </td>


      <td class="cond-cell">

        <b>
          ${escapeHtml(condition)}
        </b>

        <span>
          ${escapeHtml(
            report.symptoms ||
            ""
          )}
        </span>

      </td>


      <td>

        <span
          class="status-chip ${statusClass}"
        >

          <span class="d"></span>

          ${escapeHtml(status)}

        </span>

      </td>


      <td>

        <div class="action-btns">

          <button
            class="a-btn view"
            data-id="${reportId}"
            title="View"
          >
            👁️
          </button>


          <button
            class="a-btn download"
            data-id="${reportId}"
            title="Download"
          >
            ⬇️
          </button>


          <button
            class="a-btn delete"
            data-id="${reportId}"
            title="Delete"
          >
            🗑️
          </button>

        </div>

      </td>

    </tr>

  `;

}


/* =========================================================
   RENDER REPORTS
   ========================================================= */

function renderReports(reports) {

  filteredReports =
    reports;


  const total =
    reports.length;


  const pages =
    Math.max(
      1,
      Math.ceil(
        total / pageSize
      )
    );


  if (
    currentPage >
    pages
  ) {

    currentPage =
      pages;

  }


  const start =
    (
      currentPage - 1
    ) * pageSize;


  const pageReports =
    reports.slice(
      start,
      start + pageSize
    );


  if (!pageReports.length) {

    tableBody.innerHTML = `
      <tr>

        <td
          colspan="6"
          style="
            text-align:center;
            padding:50px;
            color:#5b6b8c;
          "
        >

          <div
            style="
              font-size:35px;
              margin-bottom:12px;
            "
          >
            📋
          </div>


          <strong>
            No consultations yet
          </strong>


          <div
            style="margin-top:6px;"
          >

            Your completed Human and Animal
            consultations will appear here.

          </div>

        </td>

      </tr>
    `;

  } else {

    tableBody.innerHTML =
      pageReports
        .map(createRow)
        .join("");

  }


  updateResultsNote(
    total
  );


  renderPagination(
    total
  );

}


/* =========================================================
   PAGINATION
   ========================================================= */

function renderPagination(total) {

  const pagination =
    document.querySelector(
      ".pagination"
    );


  if (!pagination) {
    return;
  }


  const pages =
    Math.max(
      1,
      Math.ceil(
        total / pageSize
      )
    );


  currentPage =
    Math.min(
      currentPage,
      pages
    );


  let html = `

    <button
      class="page-btn"
      data-page="prev"
      ${currentPage === 1 ? "disabled" : ""}
    >
      ‹ Previous
    </button>

  `;


  const maxButtons =
    7;


  if (pages <= maxButtons) {

    for (
      let i = 1;
      i <= pages;
      i++
    ) {

      html += `

        <button
          class="page-btn ${
            i === currentPage
              ? "active"
              : ""
          }"
          data-page="${i}"
        >
          ${i}
        </button>

      `;

    }

  } else {

    const set =
      new Set([
        1,
        currentPage,
        pages
      ]);


    if (
      currentPage > 2
    ) {

      set.add(
        currentPage - 1
      );

    }


    if (
      currentPage <
      pages - 1
    ) {

      set.add(
        currentPage + 1
      );

    }


    const nums =
      [...set].sort(
        (a, b) =>
          a - b
      );


    let previous =
      0;


    for (
      const number
      of nums
    ) {

      if (
        previous &&
        number -
          previous >
          1
      ) {

        html += `

          <button
            class="page-btn"
            disabled
          >
            ...
          </button>

        `;

      }


      html += `

        <button
          class="page-btn ${
            number ===
            currentPage
              ? "active"
              : ""
          }"
          data-page="${number}"
        >
          ${number}
        </button>

      `;


      previous =
        number;

    }

  }


  html += `

    <button
      class="page-btn"
      data-page="next"
      ${
        currentPage === pages
          ? "disabled"
          : ""
      }
    >
      Next ›
    </button>

  `;


  pagination.innerHTML =
    html;

}


/* =========================================================
   RESULTS NOTE
   ========================================================= */

function updateResultsNote(
  total
) {

  if (!resultsNote) {
    return;
  }


  if (total === 0) {

    resultsNote.textContent =
      "Showing 0 results";

    return;

  }


  const start =
    (
      currentPage - 1
    ) * pageSize + 1;


  const end =
    Math.min(
      currentPage * pageSize,
      total
    );


  resultsNote.textContent =
    `Showing ${start} to ${end} of ${total} results`;

}


/* =========================================================
   FILTERS
   ========================================================= */

function applyFilters() {

  const query =
    searchInput.value
      .trim()
      .toLowerCase();


  const selectedType =
    typeFilter.value;


  const selectedStatus =
    statusFilter.value;


  const filtered =
    allReports.filter(
      (report) => {

        const type =
          String(
            report.type ||
            "human"
          ).toLowerCase();


        const status =
          String(
            report.status ||
            "completed"
          ).toLowerCase();


        const patient =
          getPatientName(
            report
          );


        const condition =
          extractCondition(
            report.aiResult
          );


        const searchText =
          `

            ${patient}

            ${condition}

            ${report.symptoms || ""}

            ${report.type || ""}

          `
            .toLowerCase();


        const matchesSearch =
          !query ||
          searchText.includes(
            query
          );


        const matchesType =
          selectedType ===
            "all" ||
          type ===
            selectedType;


        const matchesStatus =
          selectedStatus ===
            "all" ||
          status ===
            selectedStatus;


        return (
          matchesSearch &&
          matchesType &&
          matchesStatus
        );

      }
    );


  currentPage =
    1;


  renderReports(
    filtered
  );

}


/* =========================================================
   RESET
   ========================================================= */

resetBtn.addEventListener(
  "click",
  async () => {

    searchInput.value =
      "";

    typeFilter.value =
      "all";

    statusFilter.value =
      "all";


    const user =
      auth.currentUser;


    if (!user) {

      alert(
        "Please log in again."
      );

      return;

    }


    await loadConsultations(
      user.uid
    );

  }
);


/* =========================================================
   SEARCH / FILTER EVENTS
   ========================================================= */

searchInput.addEventListener(
  "input",
  applyFilters
);


typeFilter.addEventListener(
  "change",
  applyFilters
);


statusFilter.addEventListener(
  "change",
  applyFilters
);


/* =========================================================
   TABLE BUTTONS
   ========================================================= */

tableBody.addEventListener(
  "click",
  async (event) => {

    const button =
      event.target.closest(
        ".a-btn"
      );


    if (!button) {
      return;
    }


    const reportId =
      button.dataset.id;


    if (
      button.classList.contains(
        "view"
      )
    ) {

      viewReport(
        reportId
      );

    }


    else if (
      button.classList.contains(
        "download"
      )
    ) {

      await downloadReport(
        reportId
      );

    }


    else if (
      button.classList.contains(
        "delete"
      )
    ) {

      await deleteReport(
        reportId
      );

    }

  }
);


/* =========================================================
   PAGINATION EVENTS
   ========================================================= */

const pagination =
  document.querySelector(
    ".pagination"
  );


if (pagination) {

  pagination.addEventListener(
    "click",
    (event) => {

      const button =
        event.target.closest(
          ".page-btn"
        );


      if (
        !button ||
        button.disabled
      ) {

        return;

      }


      const action =
        button.dataset.page;


      const pages =
        Math.max(
          1,
          Math.ceil(
            filteredReports.length /
              pageSize
          )
        );


      if (
        action ===
        "prev"
      ) {

        currentPage =
          Math.max(
            1,
            currentPage - 1
          );

      }


      else if (
        action ===
        "next"
      ) {

        currentPage =
          Math.min(
            pages,
            currentPage + 1
          );

      }


      else if (
        action &&
        !Number.isNaN(
          Number(action)
        )
      ) {

        currentPage =
          Number(action);

      }


      renderReports(
        filteredReports
      );

    }
  );

}


/* =========================================================
   VIEW
   ========================================================= */

function viewReport(
  reportId
) {

  const report =
    allReports.find(
      item =>
        item.id ===
        reportId
    );


  if (!report) {

    alert(
      "Report could not be found."
    );

    return;

  }


  showReportModal(
    report
  );

}


/* =========================================================
   SHOW REPORT MODAL
   ========================================================= */

function showReportModal(
  report
) {

  let modal =
    document.getElementById(
      "reportViewModal"
    );


  if (!modal) {

    modal =
      document.createElement(
        "div"
      );


    modal.id =
      "reportViewModal";


    modal.innerHTML = `

      <div
        id="reportModalOverlay"
        style="
          position:fixed;
          inset:0;
          background:rgba(18,33,62,.55);
          display:flex;
          align-items:center;
          justify-content:center;
          padding:20px;
          z-index:9999;
        "
      >

        <div
          style="
            background:#fff;
            width:min(850px,95vw);
            max-height:90vh;
            overflow:auto;
            border-radius:18px;
            padding:28px;
            box-shadow:0 20px 60px rgba(0,0,0,.25);
          "
        >

          <div
            style="
              display:flex;
              justify-content:space-between;
              align-items:center;
              gap:15px;
              margin-bottom:20px;
            "
          >

            <h2
              id="reportModalTitle"
            >
              Consultation Report
            </h2>


            <button
              id="closeReportModal"
              style="
                border:none;
                background:#f1f3f8;
                width:36px;
                height:36px;
                border-radius:50%;
                cursor:pointer;
                font-size:18px;
              "
            >
              ✕
            </button>

          </div>


          <div
            id="reportModalContent"
          ></div>


          <div
            style="
              display:flex;
              justify-content:flex-end;
              gap:10px;
              margin-top:22px;
            "
          >

            <button
              id="modalDownloadBtn"
              style="
                border:1px solid #3cb897;
                color:#278866;
                background:#fff;
                padding:11px 16px;
                border-radius:9px;
                font-weight:700;
                cursor:pointer;
              "
            >
              ⬇️ Download
            </button>


            <button
              id="modalDeleteBtn"
              style="
                border:1px solid #e15b5b;
                color:#c94b4b;
                background:#fff;
                padding:11px 16px;
                border-radius:9px;
                font-weight:700;
                cursor:pointer;
              "
            >
              🗑️ Delete
            </button>

          </div>

        </div>

      </div>

    `;


    document.body.appendChild(
      modal
    );


    document
      .getElementById(
        "closeReportModal"
      )
      .addEventListener(
        "click",
        closeReportModal
      );


    document
      .getElementById(
        "reportModalOverlay"
      )
      .addEventListener(
        "click",
        (event) => {

          if (
            event.target.id ===
            "reportModalOverlay"
          ) {

            closeReportModal();

          }

        }
      );


    document
      .getElementById(
        "modalDownloadBtn"
      )
      .addEventListener(
        "click",
        () => {

          downloadReport(
            modal.dataset.reportId
          );

        }
      );


    document
      .getElementById(
        "modalDeleteBtn"
      )
      .addEventListener(
        "click",
        () => {

          deleteReport(
            modal.dataset.reportId
          );

        }
      );

  }


  modal.dataset.reportId =
    report.id;


  const type =
    report.type ||
    "Human";


  const date =
    getReportDate(
      report
    );


  const patientName =
    getPatientName(
      report
    );


  document.getElementById(
    "reportModalTitle"
  ).textContent =
    `${type} Consultation`;


  document.getElementById(
    "reportModalContent"
  ).innerHTML = `

    <div
      style="
        display:grid;
        grid-template-columns:repeat(2,1fr);
        gap:12px;
        margin-bottom:18px;
      "
    >

      <div
        style="
          background:#f6f9fd;
          padding:14px;
          border-radius:10px;
        "
      >

        <div
          style="
            font-size:11px;
            color:#5b6b8c;
          "
        >
          Patient
        </div>


        <strong>
          ${escapeHtml(patientName)}
        </strong>

      </div>


      <div
        style="
          background:#f6f9fd;
          padding:14px;
          border-radius:10px;
        "
      >

        <div
          style="
            font-size:11px;
            color:#5b6b8c;
          "
        >
          Date
        </div>


        <strong>
          ${
            date.getTime()
              ? escapeHtml(
                  date.toLocaleString()
                )
              : "—"
          }
        </strong>

      </div>


      <div
        style="
          background:#f6f9fd;
          padding:14px;
          border-radius:10px;
        "
      >

        <div
          style="
            font-size:11px;
            color:#5b6b8c;
          "
        >
          Type
        </div>


        <strong>
          ${escapeHtml(type)}
        </strong>

      </div>


      <div
        style="
          background:#f6f9fd;
          padding:14px;
          border-radius:10px;
        "
      >

        <div
          style="
            font-size:11px;
            color:#5b6b8c;
          "
        >
          Status
        </div>


        <strong>
          ${escapeHtml(
            report.status ||
            "Completed"
          )}
        </strong>

      </div>

    </div>


    <h3
      style="
        font-size:14px;
        margin-bottom:8px;
      "
    >
      Symptoms
    </h3>


    <div
      style="
        background:#f6f9fd;
        padding:14px;
        border-radius:10px;
        white-space:pre-wrap;
        margin-bottom:18px;
      "
    >

      ${escapeHtml(
        report.symptoms ||
        "Not provided"
      )}

    </div>


    <h3
      style="
        font-size:14px;
        margin-bottom:8px;
      "
    >
      AI Analysis
    </h3>


    <div
      style="
        background:#f6f9fd;
        padding:16px;
        border-radius:10px;
        white-space:pre-wrap;
        line-height:1.6;
        max-height:420px;
        overflow:auto;
      "
    >

      ${escapeHtml(
        report.aiResult ||
        "No AI result available."
      )}

    </div>

  `;


  modal.style.display =
    "block";

}


/* =========================================================
   CLOSE MODAL
   ========================================================= */

function closeReportModal() {

  const modal =
    document.getElementById(
      "reportViewModal"
    );


  if (modal) {

    modal.style.display =
      "none";

  }

}


/* =========================================================
   DOWNLOAD
   ========================================================= */

async function downloadReport(
  reportId
) {

  const report =
    allReports.find(
      item =>
        item.id ===
        reportId
    );


  if (!report) {

    alert(
      "Report could not be found."
    );

    return;

  }


  const date =
    getReportDate(
      report
    );


  const type =
    report.type ||
    "Human";


  const patientName =
    getPatientName(
      report
    );


  const printWindow =
    window.open(
      "",
      "_blank",
      "width=900,height=700"
    );


  if (!printWindow) {

    alert(
      "Please allow pop-ups."
    );

    return;

  }


  printWindow.document.write(`

    <!DOCTYPE html>

    <html>

    <head>

      <title>
        MediScan AI Report
      </title>


      <style>

        body {
          font-family: Arial, sans-serif;
          color: #12213e;
          padding: 40px;
          line-height: 1.6;
        }

        .sub {
          color: #5b6b8c;
          margin-bottom: 25px;
        }

        .box {
          border: 1px solid #e6ebf5;
          border-radius: 10px;
          padding: 15px;
          margin-bottom: 15px;
        }

        .label {
          font-size: 12px;
          color: #5b6b8c;
          margin-bottom: 5px;
        }

        .ai {
          white-space: pre-wrap;
        }

      </style>

    </head>


    <body>

      <h1>
        MediScan AI
      </h1>


      <div class="sub">

        ${escapeHtml(type)}
        Consultation Report

      </div>


      <div class="box">

        <div class="label">
          Patient
        </div>

        <strong>
          ${escapeHtml(patientName)}
        </strong>

      </div>


      <div class="box">

        <div class="label">
          Email
        </div>

        <strong>
          ${escapeHtml(
            report.email ||
            ""
          )}
        </strong>

      </div>


      <div class="box">

        <div class="label">
          Date
        </div>

        <strong>

          ${
            date.getTime()
              ? escapeHtml(
                  date.toLocaleString()
                )
              : ""
          }

        </strong>

      </div>


      <div class="box">

        <div class="label">
          Symptoms
        </div>

        ${escapeHtml(
          report.symptoms ||
          "Not provided"
        )}

      </div>


      <div class="box">

        <div class="label">
          AI Analysis
        </div>


        <div class="ai">

          ${escapeHtml(
            report.aiResult ||
            "No AI analysis available."
          )}

        </div>

      </div>


      <div
        style="
          margin-top:30px;
          font-size:12px;
          color:#777;
        "
      >

        This report is for informational purposes only
        and is not a medical diagnosis.

      </div>


    </body>

    </html>

  `);


  printWindow.document.close();


  await new Promise(
    resolve =>
      setTimeout(
        resolve,
        300
      )
  );


  printWindow.focus();

  printWindow.print();


  const user =
    auth.currentUser;


  if (user) {

    try {

      await updateDoc(

        doc(
          db,
          "users",
          user.uid,
          "consultations",
          reportId
        ),

        {
          downloaded: true,
          downloadedAt:
            new Date()
        }

      );


      report.downloaded =
        true;

    } catch (error) {

      console.error(
        "Could not record download:",
        error
      );

    }

  }

}


/* =========================================================
   DELETE
   ========================================================= */

async function deleteReport(
  reportId
) {

  const confirmed =
    confirm(
      "Delete this consultation permanently?"
    );


  if (!confirmed) {
    return;
  }


  const user =
    auth.currentUser;


  if (!user) {

    alert(
      "Please log in again."
    );

    return;

  }


  try {

    await deleteDoc(

      doc(
        db,
        "users",
        user.uid,
        "consultations",
        reportId
      )

    );


    allReports =
      allReports.filter(
        report =>
          report.id !==
          reportId
      );


    filteredReports =
      filteredReports.filter(
        report =>
          report.id !==
          reportId
      );


    totalConsultations.textContent =
      allReports.length;


    renderReports(
      filteredReports
    );


    closeReportModal();


  } catch (error) {

    console.error(
      "Delete error:",
      error
    );


    alert(
      "Unable to delete the consultation.\n\n" +
      error.message
    );

  }

}