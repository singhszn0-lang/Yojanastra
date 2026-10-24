import { useCallback, useEffect, useMemo, useState } from "react";
import "./App.css";
import "./YojanastraExtras.css";
import { API_BASE_URL } from "./api";

const API_BASE = API_BASE_URL;

async function api(path, options = {}) {
  const token = sessionStorage.getItem("yojanastra_token");

  const headers = {
    ...(options.body instanceof FormData
      ? {}
      : { "Content-Type": "application/json" }),
    ...options.headers,
    ...(token
      ? { Authorization: `Bearer ${token}` }
      : {}),
  };

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  const body = await response.json().catch(() => ({}));

  if (!response.ok) {
    const detail = body.detail;
    throw new Error(
      typeof detail === "string"
        ? detail
        : `Request failed (${response.status})`
    );
  }

  return body;
}


const menu = [
  ["Dashboard", "▦"],
  ["Applications", "▤"],
  ["Register Member", "♙"],
  ["Submit Application", "+"],
  ["Duplicate Review", "◎"],
  ["Schemes", "▣"],
  ["Eligibility Checker", "✓"],
  ["Officer Login", "♙"],
  ["Officer Reviews", "◉"],
  ["Audit Log", "◷"],
];

function Status({ value }) {
  const text = String(value || "UNKNOWN").replaceAll("_", " ");
  return <span className={`status status-${text.toLowerCase().replaceAll(" ", "-")}`}>{text}</span>;
}

function Panel({ title, description, children, action }) {
  return <section className="panel">
    <div className="panel-heading">
      <div><h2>{title}</h2>{description && <p>{description}</p>}</div>
      {action}
    </div>
    {children}
  </section>;
}

function Empty({ children = "No records found." }) {
  return <div className="empty-state"><p>{children}</p></div>;
}

function emptyFamilyMember() {
  return {
    full_name: "",
    age: "",
    state: "",
    category: "",
    annual_income: "",
    phone: "",
    aadhaar_last4: "",
    class_12_percentile: "",
    regular_course: "",
    receives_other_scholarship: "",
    eligibility_result: null,
  };
}

function newFamilyForm() {
  return {
    household_id: `FAM-${crypto.randomUUID().slice(0, 8).toUpperCase()}`,
    family_annual_income: "",
    members: [
      {
        ...emptyFamilyMember(),
        full_name: "Shreya",
        age: "19",
        state: "West Bengal",
        category: "General",
        annual_income: "50000",
      },
    ],
  };
}

export default function App() {
  const [page, setPage] = useState("Dashboard");
  const [applications, setApplications] = useState([]);
  const [citizens, setCitizens] = useState([]);
  const [schemes, setSchemes] = useState([]);
  const [flags, setFlags] = useState([]);
  const [reviews, setReviews] = useState([]);
  const [logs, setLogs] = useState([]);
  const [stats, setStats] = useState({});
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");
  const [selectedApp, setSelectedApp] = useState(null);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  
const [token, setToken] = useState(
  () => sessionStorage.getItem("yojanastra_token") || ""
);
const [username, setUsername] = useState("officer");
const [password, setPassword] = useState("");
const [loginLoading, setLoginLoading] = useState(false);
const [reviewLoading, setReviewLoading] = useState(false);
const [reviewError, setReviewError] = useState("");

  const [applicationForm, setApplicationForm] = useState({
    citizen_id: "", scheme_id: "", household_id: ""
  });
  const [citizenForm, setCitizenForm] = useState(newFamilyForm);
  const [eligibilityForm, setEligibilityForm] = useState({
    scheme_id: "", annual_income: "", age: "", residence: ""
  });
  const [eligibilityResult, setEligibilityResult] = useState(null);
  const [reviewForm, setReviewForm] = useState({ officer_name: "Demo Officer", decision: "NOT_DUPLICATE", remarks: "" });

  
const loadAll = useCallback(async () => {
  setLoading(true);
  setError("");

  const requests = [
    api("/applications"),
    api("/citizens"),
    api("/schemes"),
    api("/duplicate-flags?review_status="),
    token ? api("/officer-reviews") : Promise.resolve([]),
    api("/audit-logs"),
    api("/dashboard/stats"),
  ];

  const results = await Promise.allSettled(requests);

  const getData = (index, fallback) =>
    results[index].status === "fulfilled"
      ? results[index].value
      : fallback;

  setApplications(
    Array.isArray(getData(0, [])) ? getData(0, []) : []
  );
  setCitizens(
    Array.isArray(getData(1, [])) ? getData(1, []) : []
  );
  setSchemes(
    Array.isArray(getData(2, [])) ? getData(2, []) : []
  );
  setFlags(
    Array.isArray(getData(3, [])) ? getData(3, []) : []
  );
  setReviews(
    Array.isArray(getData(4, [])) ? getData(4, []) : []
  );
  setLogs(
    Array.isArray(getData(5, [])) ? getData(5, []) : []
  );
  setStats(getData(6, {}) || {});

  const failed = results
    .map((result, index) => ({
      result,
      path: [
        "/applications",
        "/citizens",
        "/schemes",
        "/duplicate-flags",
        "/officer-reviews",
        "/audit-logs",
        "/dashboard/stats",
      ][index],
    }))
    .filter(item => item.result.status === "rejected");

  if (failed.length > 0) {
    setError(
      `Backend requests failed: ${failed.map(item => `${item.path} (${item.result.reason.message})`).join("; ")}`
    );
  }

  setLoading(false);
}, [token]);


async function handleLogin(event) {
  event.preventDefault();
  setLoginLoading(true);
  setError("");

  try {
    const response = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: new URLSearchParams({
        username,
        password,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(
        data.detail || "Login failed. Check your credentials."
      );
    }

    sessionStorage.setItem("yojanastra_token", data.access_token);
    setToken(data.access_token);
    setPage("Applications");
    setPassword("");
    setNotice("Officer login successful.");

  } catch (err) {
    setError(err.message);
  } finally {
    setLoginLoading(false);
  }
}

function handleLogout() {
  sessionStorage.removeItem("yojanastra_token");
  setToken("");
  setReviews([]);
  setNotice("Logged out successfully.");
}



useEffect(() => {
  void Promise.resolve().then(loadAll);
}, [loadAll, token]);


  const filteredApps = useMemo(() => applications.filter(a => {
    const q = query.trim().toLowerCase();
    const matchesQuery = !q || [a.applicant_name, a.citizen_id, a.application_id, a.scheme_name]
      .some(v => String(v ?? "").toLowerCase().includes(q));
    return matchesQuery && (statusFilter === "All" || a.status === statusFilter);
  }), [applications, query, statusFilter]);

  function flash(message) {
    setNotice(message);
    setError("");
    window.setTimeout(() => setNotice(""), 4500);
  }

  function openApplication(app) {
    setSelectedApp(app);
    setReviewError("");
    setReviewForm({ officer_name: "Demo Officer", decision: "APPROVE", remarks: "" });
  }

  async function registerFamily(e) {
    e.preventDefault();
    try {
      const incompleteMember = citizenForm.members.find(member =>
        !member.full_name.trim() || !member.state.trim()
      );
      if (incompleteMember) {
        throw new Error("Every family member needs a full name and state.");
      }

      const result = await api("/families", {
        method: "POST",
        body: JSON.stringify({
          household_id: citizenForm.household_id.trim(),
          members: citizenForm.members.map(member => ({
            full_name: member.full_name.trim(),
            age: member.age === "" ? null : Number(member.age),
            state: member.state.trim(),
            category: member.category.trim() || null,
            annual_income: member.annual_income === "" ? null : Number(member.annual_income),
            phone: member.phone.trim() || null,
            aadhaar_last4: member.aadhaar_last4.trim() || null,
            family_annual_income: citizenForm.family_annual_income === "" ? null : Number(citizenForm.family_annual_income),
            class_12_percentile: member.class_12_percentile === "" ? null : Number(member.class_12_percentile),
            regular_course: member.regular_course === "" ? null : member.regular_course === "true",
            receives_other_scholarship: member.receives_other_scholarship === "" ? null : member.receives_other_scholarship === "true",
          })),
        }),
      });
      const firstMember = result.members[0];
      setCitizenForm(newFamilyForm);
      setApplicationForm(form => ({
        ...form,
        citizen_id: String(firstMember.citizen_id),
        household_id: result.household_id,
      }));
      await loadAll();
      setPage("Submit Application");
      flash(`${result.message}. Household ID: ${result.household_id}.`);
    } catch (e) {
      setError(e.message);
    }
  }

  async function checkFamilyMemberEligibility(index) {
    try {
      const member = citizenForm.members[index];
      const result = await api("/eligibility/csss-preview", {
        method: "POST",
        body: JSON.stringify({
          family_annual_income: citizenForm.family_annual_income === "" ? null : Number(citizenForm.family_annual_income),
          class_12_percentile: member.class_12_percentile === "" ? null : Number(member.class_12_percentile),
          regular_course: member.regular_course === "" ? null : member.regular_course === "true",
          receives_other_scholarship: member.receives_other_scholarship === "" ? null : member.receives_other_scholarship === "true",
        }),
      });
      setCitizenForm(form => ({
        ...form,
        members: form.members.map((row, rowIndex) =>
          rowIndex === index ? { ...row, eligibility_result: result } : row
        ),
      }));
    } catch (e) {
      setError(e.message);
    }
  }

  async function submitApplication(e) {
    e.preventDefault();
    try {
      const payload = {
        citizen_id: applicationForm.citizen_id.trim(),
        scheme_id: Number(applicationForm.scheme_id),
        household_id: applicationForm.household_id.trim() || null,
      };
      const result = await api("/applications", { method: "POST", body: JSON.stringify(payload) });
      setApplicationForm({ citizen_id: "", scheme_id: "", household_id: "" });
      flash(`Application #${result.application_id} submitted. Status: ${result.status}${result.possible_duplicate ? " — flagged for officer review." : "."}`);
      await loadAll();
      setPage("Applications");
    } catch (e) { setError(e.message); }
  }

  async function submitEligibility(e) {
    e.preventDefault();
    try {
      const payload = {
        scheme_id: eligibilityForm.scheme_id ? Number(eligibilityForm.scheme_id) : null,
        annual_income: eligibilityForm.annual_income === "" ? null : Number(eligibilityForm.annual_income),
        age: eligibilityForm.age === "" ? null : Number(eligibilityForm.age),
        residence: eligibilityForm.residence.trim() || null,
      };
      setEligibilityResult(await api("/eligibility/check", { method: "POST", body: JSON.stringify(payload) }));
    } catch (e) { setError(e.message); }
  }

  async function submitReview(target, decision = reviewForm.decision) {
    setReviewLoading(true);
    setReviewError("");
    try {
      const payload = {
        application_id: Number(target.application_id),
        officer_name: reviewForm.officer_name.trim(),
        decision,
        remarks: reviewForm.remarks.trim(),
      };
      if (!payload.officer_name || !payload.remarks) {
        setReviewError("Please enter review remarks before deciding.");
        return;
      }
      const result = await api("/officer-reviews", { method: "POST", body: JSON.stringify(payload) });
      setSelectedApp(null);
      setReviewForm({ officer_name: "Demo Officer", decision: "NOT_DUPLICATE", remarks: "" });
      flash(result.message || "Officer review saved.");
      await loadAll();
    } catch (e) {
      setReviewError(e.message);
    } finally {
      setReviewLoading(false);
    }
  }

  const pageTitle = page;
  const pageSubtitle = {
    Dashboard: "Public benefit applications ka live overview.",
    Applications: "Search, filter aur application details review karo.",
    "Register Member": "Naye member ki details save karke citizen ID generate karo.",
    "Submit Application": "Registered member ko scheme ke liye apply karo.",
    "Duplicate Review": "Possible repeat applications ko human review ke liye check karo.",
    Schemes: "Backend se available benefit schemes.",
    "Eligibility Checker": "Backend eligibility logic aur evidence explanation check karo.",
    "Officer Reviews": "Officer ke saved review decisions.",
    "Audit Log": "Recent system aur officer activity records.",
    "Officer Login": "Secure access for authorized officers."
  }[page];

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-logo"> 

{token && (
  <button
    className="secondary-button action-button"
    onClick={handleLogout}
  >
    Logout
  </button>
)}


</div><div><h2>Yojanastra</h2><p>Benefit Intelligence System</p></div></div>
      <p className="nav-heading">WORKSPACE</p>
      <nav className="nav-list">
        {menu.map(([label, icon]) => <button key={label} className={`nav-item ${page === label ? "active" : ""}`} onClick={() => { setPage(label); setError(""); }}>
          <span className="nav-icon">{icon}</span>{label}
        </button>)}
      </nav>
      <div className="sidebar-note"><strong><span className="online-dot" /> PostgreSQL connected</strong><p>Application, scheme, review, and audit data is loaded from the backend database.</p></div>
    </aside>

    <main className="main-content">
      <header className="topbar">
        <div><p className="eyebrow">YOJANASTRA / OFFICER CONSOLE</p><h1>{pageTitle}</h1><p className="subtitle">{pageSubtitle}</p></div>
        <div className="header-actions"><span className="header-badge"><span className="online-dot" /> API {error ? "needs attention" : "connected / checking"}</span><button className="secondary-button action-button" onClick={loadAll} disabled={loading}>{loading ? "Refreshing…" : "↻ Refresh"}</button></div>
      </header>

      {notice && <div className="notice"><span>{notice}</span><button onClick={() => setNotice("")}>×</button></div>}
      {error && <div className="error-banner"><strong>Something went wrong</strong><p>{error}</p><button className="secondary-button" onClick={() => setError("")}>Dismiss</button></div>}
      {loading && <p className="loading-line">Loading latest data from backend…</p>}

      {page === "Dashboard" && <>
        <section className="welcome-card"><div><span className="welcome-label">BENEFIT INTELLIGENCE</span><h2>Welcome to Yojanastra</h2><p>Applications ko track karo, potential duplicates flag karo aur transparent officer review maintain karo.</p></div><div className="welcome-icon">✦</div></section>
        <div className="stats-grid">
          {[
            ["Total Applications", stats.total_applications ?? applications.length, "blue", "▤"],
            ["Pending Applications", stats.pending_applications ?? applications.filter(a => a.status === "PENDING").length, "orange", "◷"],
            ["Duplicate Flags", stats.total_duplicate_flags ?? flags.length, "red", "◎"],
            ["Active Schemes", stats.total_schemes ?? schemes.length, "green", "▣"]
          ].map(([label, value, color, icon]) => <div className="stat-card" key={label}><div className="stat-top"><span>{label}</span><span className={`stat-icon ${color}`}>{icon}</span></div><strong>{value}</strong><small>Backend-reported count</small></div>)}
        </div>
        <Panel title="Recent Applications" description="Latest applications returned by the API" action={<button className="view-button" onClick={() => setPage("Applications")}>View all →</button>}>
          <ApplicationsTable rows={applications.slice(0, 5)} onView={openApplication} />
        </Panel>
        <div className="two-column-panels"><Panel title="Review Queue" description="Possible duplicates requiring attention"><p className="summary-number">{flags.filter(f => ["PENDING", "NEEDS_INFO"].includes(f.review_status)).length}</p><button className="primary-button action-button" onClick={() => setPage("Duplicate Review")}>Open duplicate review</button></Panel>
        <Panel title="System status" description="Current configuration"><p>API: <strong>{error ? "Check connection" : "FastAPI"}</strong></p><p>Storage: <strong>PostgreSQL</strong></p><p>Database: <strong>{error ? "Check connection" : "Connected"}</strong></p></Panel></div>
      </>}

      {page === "Applications" && <Panel title="Applications" description="Search by applicant, citizen ID, application ID or scheme." action={<button className="primary-button action-button" onClick={() => setPage("Submit Application")}>+ New application</button>}>
        <div className="toolbar"><input className="search-input" placeholder="Search applications…" value={query} onChange={e => setQuery(e.target.value)} /><select className="filter-select" value={statusFilter} onChange={e => setStatusFilter(e.target.value)}><option>All</option><option value="PENDING">Pending</option><option value="APPROVED">Approved</option><option value="REJECTED">Rejected</option></select></div>
        <ApplicationsTable rows={filteredApps} onView={openApplication} />
      </Panel>}

      {page === "Register Member" && <Panel title="Register a family" description="Add as many family members as needed. Preview PM-USP CSSS eligibility for each member and review any flagged rules.">
        <form className="data-form family-form" onSubmit={registerFamily}>
          <label className="family-id-field">Household ID *<input required maxLength="100" value={citizenForm.household_id} onChange={e => setCitizenForm({...citizenForm, household_id:e.target.value})} /></label>
          <label className="family-id-field">Annual family income (₹)<input type="number" min="0" step="0.01" value={citizenForm.family_annual_income} onChange={e => setCitizenForm(form => ({...form, family_annual_income:e.target.value, members:form.members.map(member => ({...member, eligibility_result:null}))}))} /><small>Used for the CSSS preview; this is separate from each member's individual income.</small></label>
          {citizenForm.members.map((member, index) => {
            return <fieldset className="family-member" key={index}>
              <legend>Family member {index + 1}</legend>
              {citizenForm.members.length > 1 && <button className="remove-member-button" type="button" onClick={() => setCitizenForm(form => ({...form, members:form.members.filter((_, rowIndex) => rowIndex !== index)}))}>Remove member</button>}
              <label>Full name *<input required maxLength="120" value={member.full_name} onChange={e => setCitizenForm(form => ({...form, members:form.members.map((row, rowIndex) => rowIndex === index ? {...row, full_name:e.target.value} : row)}))} placeholder="Member's full name" /></label>
              <label>Age<input type="number" min="0" max="120" value={member.age} onChange={e => setCitizenForm(form => ({...form, members:form.members.map((row, rowIndex) => rowIndex === index ? {...row, age:e.target.value} : row)}))} /></label>
              <label>State *<input required maxLength="100" value={member.state} onChange={e => setCitizenForm(form => ({...form, members:form.members.map((row, rowIndex) => rowIndex === index ? {...row, state:e.target.value} : row)}))} placeholder="e.g. West Bengal" /></label>
              <label>Category<input maxLength="30" value={member.category} onChange={e => setCitizenForm(form => ({...form, members:form.members.map((row, rowIndex) => rowIndex === index ? {...row, category:e.target.value} : row)}))} placeholder="Optional" /></label>
              <label>Annual income (₹)<input type="number" min="0" step="0.01" value={member.annual_income} onChange={e => setCitizenForm(form => ({...form, members:form.members.map((row, rowIndex) => rowIndex === index ? {...row, annual_income:e.target.value} : row)}))} /></label>
              <label>Phone number<input type="tel" maxLength="20" value={member.phone} onChange={e => setCitizenForm(form => ({...form, members:form.members.map((row, rowIndex) => rowIndex === index ? {...row, phone:e.target.value} : row)}))} placeholder="Optional" /></label>
              <label>Aadhaar last 4 digits<input inputMode="numeric" pattern="[0-9]{4}" maxLength="4" value={member.aadhaar_last4} onChange={e => setCitizenForm(form => ({...form, members:form.members.map((row, rowIndex) => rowIndex === index ? {...row, aadhaar_last4:e.target.value.replace(/\D/g, "").slice(0, 4)} : row)}))} placeholder="Optional; full Aadhaar is not stored" /></label>
              <label>Class XII board percentile<input type="number" min="0" max="100" step="0.01" value={member.class_12_percentile} onChange={e => setCitizenForm(form => ({...form, members:form.members.map((row, rowIndex) => rowIndex === index ? {...row, class_12_percentile:e.target.value, eligibility_result:null} : row)}))} placeholder="0–100" /></label>
              <label>Enrolled in a regular degree course<select value={member.regular_course} onChange={e => setCitizenForm(form => ({...form, members:form.members.map((row, rowIndex) => rowIndex === index ? {...row, regular_course:e.target.value, eligibility_result:null} : row)}))}><option value="">Not provided</option><option value="true">Yes</option><option value="false">No</option></select></label>
              <label>Receiving another scholarship<select value={member.receives_other_scholarship} onChange={e => setCitizenForm(form => ({...form, members:form.members.map((row, rowIndex) => rowIndex === index ? {...row, receives_other_scholarship:e.target.value, eligibility_result:null} : row)}))}><option value="">Not provided</option><option value="false">No</option><option value="true">Yes</option></select></label>
              <div className="family-eligibility">
                <button className="secondary-button" type="button" onClick={() => checkFamilyMemberEligibility(index)}>Check PM-USP CSSS rules</button>
                {member.eligibility_result && <div className="eligibility-preview"><strong>{member.eligibility_result.status.replaceAll("_", " ")}</strong><ul>{member.eligibility_result.flags.map(flag => <li key={flag.rule}><Status value={flag.status} /> {flag.rule}: {flag.requirement}</li>)}</ul><small>{member.eligibility_result.note}</small></div>}
              </div>
            </fieldset>;
          })}
          <div className="form-actions"><button className="secondary-button" type="button" onClick={() => setCitizenForm(form => ({...form, members:[...form.members, emptyFamilyMember()]}))}>+ Add family member</button><button className="primary-button" type="submit">Register family members</button><button className="secondary-button" type="button" onClick={() => setCitizenForm(form => ({...form, members:[emptyFamilyMember()]}))}>Clear member details</button></div>
        </form>
      </Panel>}

      {page === "Submit Application" && <Panel title="Submit an application" description="Choose a registered member. Reuse the same member and scheme to check for a possible duplicate.">
        <form className="data-form" onSubmit={submitApplication}>
          <label>Registered member *<select required value={applicationForm.citizen_id} onChange={e => {const member=citizens.find(c=>String(c.citizen_id)===e.target.value);setApplicationForm({...applicationForm, citizen_id:e.target.value, household_id:member?.household_id || ""});}}><option value="">Select a registered member</option>{citizens.map(c => <option key={c.citizen_id} value={c.citizen_id}>#{c.citizen_id} — {c.full_name} ({c.state}){c.household_id ? ` · ${c.household_id}` : ""}</option>)}</select></label>
          {citizens.length === 0 && <p>No members are registered yet. <button className="view-button" type="button" onClick={() => setPage("Register Member")}>Register a new member</button></p>}
          <label>Scheme *<select required value={applicationForm.scheme_id} onChange={e => setApplicationForm({...applicationForm, scheme_id:e.target.value})}><option value="">Select a scheme</option>{schemes.filter(s => s.is_active).map(s => <option key={s.scheme_id} value={s.scheme_id}>{s.name}</option>)}</select></label>
          <label>Household ID<input maxLength="100" value={applicationForm.household_id} onChange={e => setApplicationForm({...applicationForm, household_id:e.target.value})} placeholder="Optional synthetic household ID" /></label>
          <div className="form-actions"><button className="primary-button" type="submit">Submit application</button><button className="secondary-button" type="button" onClick={() => setApplicationForm({citizen_id:"",scheme_id:"",household_id:""})}>Clear form</button></div>
        </form>
      </Panel>}

      {page === "Duplicate Review" && <Panel title="Duplicate review queue" description="A match is only a signal; an officer must review it.">
        {flags.length === 0 ? <Empty>No duplicate flags returned. Submit another application using the same citizen ID and scheme to test this workflow.</Empty> :
        <div className="table-wrapper"><table><thead><tr><th>Flag</th><th>Application</th><th>Matched application</th><th>Rule</th><th>Review status</th><th>Created</th><th>Action</th></tr></thead><tbody>{flags.map(f => <tr key={f.flag_id}><td>#{f.flag_id}</td><td>#{f.application_id}</td><td>#{f.matched_application_id}</td><td><strong>{f.rule_code}</strong><span className="cell-subtitle">{f.reason}</span></td><td><Status value={f.review_status}/></td><td>{formatDate(f.created_at)}</td><td><button className="view-button" disabled={!["PENDING","NEEDS_INFO"].includes(f.review_status)} onClick={() => {const a=applications.find(x=>x.application_id===f.application_id);setSelectedApp({...a, _flag:f});setReviewForm({officer_name:"Demo Officer",decision:"NOT_DUPLICATE",remarks:""});}}>Review</button></td></tr>)}</tbody></table></div>}
      </Panel>}

      {page === "Schemes" && <Panel title="Available schemes" description="Scheme details loaded from the FastAPI backend." action={<span className="record-count">{schemes.length} schemes</span>}>
        {schemes.length === 0 ? <Empty>No schemes returned by backend.</Empty> : <div className="scheme-grid">{schemes.map(s => <article className="scheme-card" key={s.scheme_id}><div className="scheme-card-top"><span className="scheme-symbol">▣</span><Status value={s.is_active ? "ACTIVE" : "INACTIVE"}/></div><p className="eyebrow">{s.category || "GENERAL"}</p><h3>{s.name}</h3><p>{s.description || "No description available."}</p><div className="scheme-card-actions"><button className="primary-button" disabled={!s.is_active} onClick={() => {setApplicationForm({...applicationForm, scheme_id:String(s.scheme_id)});setPage("Submit Application");}}>Apply in demo</button><button className="secondary-button" onClick={() => setSelectedApp({ _scheme:s })}>Details</button></div></article>)}</div>}
      </Panel>}

      {page === "Eligibility Checker" && <Panel title="Eligibility checker" description="Uses the backend /eligibility/check endpoint. This is a demo result, not an official eligibility decision.">
        <form className="data-form" onSubmit={submitEligibility}>
          <label>Scheme (optional)<select value={eligibilityForm.scheme_id} onChange={e=>setEligibilityForm({...eligibilityForm,scheme_id:e.target.value})}><option value="">Not specified</option>{schemes.map(s=><option key={s.scheme_id} value={s.scheme_id}>{s.name}</option>)}</select></label>
          <label>Annual income (₹)<input type="number" min="0" value={eligibilityForm.annual_income} onChange={e=>setEligibilityForm({...eligibilityForm,annual_income:e.target.value})}/></label>
          <label>Age<input type="number" min="0" max="120" value={eligibilityForm.age} onChange={e=>setEligibilityForm({...eligibilityForm,age:e.target.value})}/></label>
          <label>Residence / district<input value={eligibilityForm.residence} onChange={e=>setEligibilityForm({...eligibilityForm,residence:e.target.value})} placeholder="e.g. Lucknow"/></label>
          <div className="form-actions"><button className="primary-button" type="submit">Check eligibility</button><button className="secondary-button" type="button" onClick={()=>{setEligibilityForm({scheme_id:"",annual_income:"",age:"",residence:""});setEligibilityResult(null);}}>Reset</button></div>
        </form>
        {eligibilityResult && <div className="result-card"><h3>Eligibility result</h3><pre>{JSON.stringify(eligibilityResult, null, 2)}</pre><p><strong>Evidence note:</strong> {eligibilityResult.evidence_note || "No evidence note returned."}</p>{Array.isArray(eligibilityResult.evidence) && <ul>{eligibilityResult.evidence.map((item,i)=><li key={i}>{typeof item === "string" ? item : JSON.stringify(item)}</li>)}</ul>}</div>}
      </Panel>}
      
{page === "Officer Login" && (
  <Panel
    title="Officer Login"
    description="Authorized officers ke liye secure access."
  >
    {token ? (
      <div className="result-card">
        <h3>Officer already logged in</h3>
        <p>You are authenticated.</p>
        <button
          className="primary-button"
          onClick={() => setPage("Applications")}
        >
          Review applications
        </button>
      </div>
    ) : (
      <form className="data-form" onSubmit={handleLogin}>
        <label>
          Officer Username
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Enter username"
            required
          />
        </label>

        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Enter password"
            required
          />
        </label>

        <button
          className="primary-button"
          type="submit"
          disabled={loginLoading}
        >
          {loginLoading ? "Logging in..." : "Login securely"}
        </button>

        <p>Demo username: officer</p>
        <p>Demo password: DemoPass123!</p>
      </form>
    )}
  </Panel>
)}


      {page === "Officer Reviews" && <Panel title="Officer reviews" description="Review decisions recorded by the backend.">
        {reviews.length === 0 ? <Empty>No officer reviews have been saved yet.</Empty> : <div className="table-wrapper"><table><thead><tr><th>Review</th><th>Application</th><th>Officer</th><th>Decision</th><th>Remarks</th><th>Created</th></tr></thead><tbody>{reviews.map(r=><tr key={r.review_id}><td>#{r.review_id}</td><td>#{r.application_id}</td><td>{r.officer_name}</td><td><Status value={r.decision}/></td><td className="remarks-cell">{r.remarks}</td><td>{formatDate(r.created_at)}</td></tr>)}</tbody></table></div>}
      </Panel>}

      {page === "Audit Log" && <Panel title="Audit log" description="Latest 100 events returned by the API.">
        {logs.length === 0 ? <Empty>No audit events yet. Submit an application or record an officer review to generate events.</Empty> : <div className="table-wrapper"><table><thead><tr><th>Time</th><th>Actor</th><th>Action</th><th>Entity</th><th>Details</th></tr></thead><tbody>{logs.map(l=><tr key={l.log_id}><td>{formatDate(l.created_at)}</td><td>{l.actor_role}<span className="cell-subtitle">{l.actor_id}</span></td><td><strong>{l.action}</strong></td><td>{l.entity_type} #{l.entity_id}</td><td className="remarks-cell">{JSON.stringify(l.details)}</td></tr>)}</tbody></table></div>}
      </Panel>}

      <footer className="footer"><span>Yojanastra · Synthetic demo environment</span><span>Human review required for flagged cases</span></footer>
    </main>

    {selectedApp && <div className="modal-backdrop" onClick={() => setSelectedApp(null)}><div className="modal-card" onClick={e => e.stopPropagation()}>
      <div className="modal-header"><h2>{selectedApp._scheme ? "Scheme details" : "Application details"}</h2><button className="close-button" onClick={() => setSelectedApp(null)}>×</button></div>
      {selectedApp._scheme ? <><h3>{selectedApp._scheme.name}</h3><p className="modal-description">{selectedApp._scheme.description}</p><div className="detail-grid"><div><label>Scheme ID</label><p>{selectedApp._scheme.scheme_id}</p></div><div><label>Category</label><p>{selectedApp._scheme.category}</p></div><div><label>Status</label><p>{selectedApp._scheme.is_active ? "Active" : "Inactive"}</p></div></div><div className="modal-actions"><button className="primary-button" onClick={()=>{setApplicationForm({...applicationForm,scheme_id:String(selectedApp._scheme.scheme_id)});setSelectedApp(null);setPage("Submit Application");}}>Start application</button></div></> :
      <><p className="modal-description">Application details returned from backend. Use synthetic records only.</p><div className="detail-grid">
        <div><label>Application ID</label><p>#{selectedApp.application_id}</p></div><div><label>Applicant</label><p>{selectedApp.applicant_name || "—"}</p></div><div><label>Citizen ID</label><p>{selectedApp.citizen_id || "—"}</p></div><div><label>Scheme</label><p>{selectedApp.scheme_name || "—"}</p></div><div><label>Annual income</label><p>{selectedApp.annual_income == null ? "Not provided" : `₹${selectedApp.annual_income}`}</p></div><div><label>Household ID</label><p>{selectedApp.household_id || "—"}</p></div><div><label>Status</label><p><Status value={selectedApp.status}/></p></div><div><label>Submitted</label><p>{formatDate(selectedApp.created_at)}</p></div>
      </div>
      {selectedApp._flag && token && <div className="review-form"><h3>Officer review</h3><label>Officer name<input value={reviewForm.officer_name} onChange={e=>setReviewForm({...reviewForm,officer_name:e.target.value})}/></label><label>Decision<select value={reviewForm.decision} onChange={e=>setReviewForm({...reviewForm,decision:e.target.value})}><option value="NOT_DUPLICATE">Not duplicate</option><option value="CONFIRMED_DUPLICATE">Confirmed duplicate</option><option value="NEEDS_INFO">Needs more information</option><option value="APPROVE">Approve</option><option value="REJECT">Reject</option></select></label><label>Remarks *<textarea required value={reviewForm.remarks} onChange={e=>{setReviewForm({...reviewForm,remarks:e.target.value});setReviewError("");}} placeholder="Explain the reason for this decision."/></label><p className="review-warning">Possible duplicate flags are decision-support signals, not proof of fraud. Record the reason for your decision.</p>{reviewError && <p className="review-error" role="alert">{reviewError}</p>}<div className="modal-actions"><button className="secondary-button" onClick={()=>setSelectedApp(null)}>Cancel</button><button className="primary-button" disabled={reviewLoading} onClick={()=>submitReview(selectedApp._flag)}>{reviewLoading ? "Saving..." : "Save review"}</button></div></div>}
      {selectedApp._flag && !token && <div className="review-form"><p>Officer login is required to record a review.</p><div className="modal-actions"><button className="secondary-button" onClick={()=>setSelectedApp(null)}>Close</button><button className="primary-button" onClick={()=>{setSelectedApp(null);setPage("Officer Login");}}>Officer login to review</button></div></div>}
      {!selectedApp._flag && selectedApp.application_id && token && selectedApp.status === "PENDING" && <div className="review-form"><h3>Officer decision</h3><p>Review the application details, then accept or reject this pending application. A reason is required.</p><label>Review remarks *<textarea required value={reviewForm.remarks} onChange={e=>{setReviewForm({...reviewForm,remarks:e.target.value});setReviewError("");}} placeholder="Explain the reason for your decision."/></label>{reviewError && <p className="review-error" role="alert">{reviewError}</p>}<div className="modal-actions"><button className="secondary-button" onClick={()=>setSelectedApp(null)}>Cancel</button><button className="primary-button" disabled={reviewLoading} onClick={()=>submitReview(selectedApp, "APPROVE")}>{reviewLoading ? "Saving..." : "Accept application"}</button><button className="danger-button" disabled={reviewLoading} onClick={()=>submitReview(selectedApp, "REJECT")}>{reviewLoading ? "Saving..." : "Reject application"}</button></div></div>}
      {!selectedApp._flag && <div className="modal-actions"><button className="secondary-button" onClick={()=>setSelectedApp(null)}>Close</button>{selectedApp.application_id && !token && selectedApp.status === "PENDING" && <button className="primary-button" onClick={()=>{setSelectedApp(null);setPage("Officer Login");}}>Officer login to review</button>}</div>}
      </>}
    </div></div>}
  </div>;
}

function ApplicationsTable({ rows, onView }) {
  if (!rows?.length) return <Empty>No applications yet. Submit a synthetic demo application to test the workflow.</Empty>;
  return <div className="table-wrapper"><table><thead><tr><th>Application</th><th>Applicant</th><th>Scheme</th><th>Citizen ID</th><th>Status</th><th>Submitted</th><th>Action</th></tr></thead><tbody>
    {rows.map(a=><tr key={a.application_id}><td><span className="application-id">YOJ-{String(a.application_id).padStart(4,"0")}</span></td><td><strong>{a.applicant_name}</strong></td><td>{a.scheme_name || `Scheme #${a.scheme_id}`}</td><td>{a.citizen_id}</td><td><Status value={a.status}/></td><td>{formatDate(a.created_at)}</td><td><button className="view-button" onClick={()=>onView(a)}>View details</button></td></tr>)}
  </tbody></table></div>;
}

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
}
