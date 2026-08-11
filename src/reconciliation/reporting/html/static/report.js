// Presentation-only interactivity. This script filters and reveals rows based
// on client-side presentation state; it never modifies the embedded engine
// data (report state is client-side only). Uses only native controls so the
// report remains keyboard operable (REQ-238).
(function () {
  "use strict";
  var statusFilter = document.getElementById("status-filter");
  var textFilter = document.getElementById("text-filter");
  var table = document.getElementById("issues-table");
  if (!table) { return; }
  var body = table.tBodies[0];

  function rowMatches(row, status, text) {
    var rowStatus = row.getAttribute("data-status") || "";
    if (status && rowStatus !== status) { return false; }
    if (text) {
      var haystack = (row.getAttribute("data-search") || "").toLowerCase();
      if (haystack.indexOf(text) === -1) { return false; }
    }
    return true;
  }

  function apply() {
    var status = statusFilter ? statusFilter.value : "";
    var text = textFilter ? textFilter.value.trim().toLowerCase() : "";
    var rows = body.rows;
    var i;
    // Rows come in pairs: a data row followed by an optional detail row that
    // shares the same data-status. Toggle visibility without altering content.
    for (i = 0; i < rows.length; i++) {
      var row = rows[i];
      row.hidden = !rowMatches(row, status, text);
    }
  }

  if (statusFilter) { statusFilter.addEventListener("change", apply); }
  if (textFilter) { textFilter.addEventListener("input", apply); }
})();
