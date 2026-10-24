
/* Yojanastra additional frontend styling */
import { useCallback, useEffect, useMemo, useState } from "react";
import "./App.css";
import "./YojanastraExtras.css";
.nav-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  cursor: pointer;
  text-align: left;
}

.nav-item.active {
  font-weight: 600;
}

button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 18px;
}

.data-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
}

.data-form label,
.review-form label {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.data-form input,
.data-form select,
.review-form input,
.review-form select,
.review-form textarea {
  width: 100%;
  padding: 10px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
}

.form-actions,
.modal-actions,
.scheme-card-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  grid-column: 1 / -1;
}

.scheme-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
}

.scheme-card,
.result-card {
  padding: 18px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

@media (max-width: 700px) {
  .data-form,
  .detail-grid {
    grid-template-columns: 1fr;
  }

  .nav-list {
    flex-wrap: wrap;
  }

  .nav-item {
    display: flex !important;
  }

  .header-actions {
    flex-wrap: wrap;
  }
}
