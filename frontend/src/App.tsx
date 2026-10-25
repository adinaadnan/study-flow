import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type FormEvent,
} from "react";
import {
  ApiError,
  createCommitment,
  deleteCommitment,
  getCommitments,
  getCurrentUser,
  login,
  logout,
  setCommitmentCompletion,
  updateCommitment,
} from "../api";
import type {
  Commitment,
  CommitmentInput,
  CommitmentType,
  User,
} from "../types";

const TYPE_LABELS: Record<CommitmentType, string> = {
  assignment: "Assignment",
  work: "Work",
  event: "Event",
  personal: "Personal",
};

const TYPE_ICONS: Record<CommitmentType, string> = {
  assignment: "A",
  work: "W",
  event: "E",
  personal: "P",
};

const EMPTY_FORM: CommitmentInput = {
  title: "",
  type: "assignment",
  date: "",
  start_time: null,
  end_time: null,
  description: null,
};

function todayValue() {
  const today = new Date();
  const offset = today.getTimezoneOffset() * 60_000;
  return new Date(today.getTime() - offset).toISOString().slice(0, 10);
}

function sortCommitments(items: Commitment[]) {
  return [...items].sort((left, right) => {
    const dateComparison = left.date.localeCompare(right.date);
    if (dateComparison !== 0) return dateComparison;
    if (!left.start_time) return right.start_time ? 1 : left.id - right.id;
    if (!right.start_time) return -1;
    return left.start_time.localeCompare(right.start_time) || left.id - right.id;
  });
}

function formatDate(date: string) {
  return new Intl.DateTimeFormat(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
  }).format(new Date(`${date}T12:00:00`));
}

function formatTime(start: string | null, end: string | null) {
  if (!start && !end) return "Any time";
  const format = (value: string) =>
    new Intl.DateTimeFormat(undefined, {
      hour: "numeric",
      minute: "2-digit",
    }).format(new Date(`2000-01-01T${value}`));
  if (start && end) return `${format(start)} – ${format(end)}`;
  return start ? format(start) : `Until ${format(end!)}`;
}

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [authChecking, setAuthChecking] = useState(true);
  const [commitments, setCommitments] = useState<Commitment[]>([]);
  const [loadingCommitments, setLoadingCommitments] = useState(false);
  const [pageError, setPageError] = useState("");
  const [loginError, setLoginError] = useState("");
  const [loginPending, setLoginPending] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Commitment | null>(null);
  const [form, setForm] = useState<CommitmentInput>(EMPTY_FORM);
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [filter, setFilter] = useState<"all" | "upcoming" | "completed">("all");

  const loadCommitments = useCallback(async () => {
    setLoadingCommitments(true);
    setPageError("");
    try {
      setCommitments(sortCommitments(await getCommitments()));
    } catch (error) {
      setPageError(errorMessage(error));
    } finally {
      setLoadingCommitments(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    getCurrentUser()
      .then((currentUser) => {
        if (active) setUser(currentUser);
      })
      .catch((error: unknown) => {
        if (active && (!(error instanceof ApiError) || error.status !== 401)) {
          setPageError(errorMessage(error));
        }
      })
      .finally(() => {
        if (active) setAuthChecking(false);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (user) void loadCommitments();
  }, [user, loadCommitments]);

  const visibleCommitments = useMemo(() => {
    if (filter === "completed") return commitments.filter((item) => item.completed);
    if (filter === "upcoming")
      return commitments.filter((item) => !item.completed && item.date >= todayValue());
    return commitments;
  }, [commitments, filter]);

  const openNewCommitment = () => {
    setEditing(null);
    setForm({ ...EMPTY_FORM, date: todayValue() });
    setFormError("");
    setModalOpen(true);
  };

  const openEditCommitment = (commitment: Commitment) => {
    setEditing(commitment);
    setForm({
      title: commitment.title,
      type: commitment.type,
      date: commitment.date,
      start_time: commitment.start_time,
      end_time: commitment.end_time,
      description: commitment.description,
    });
    setFormError("");
    setModalOpen(true);
  };

  const submitLogin = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoginError("");
    setLoginPending(true);
    try {
      setUser(await login(email.trim(), password));
      setPassword("");
    } catch (error) {
      setLoginError(errorMessage(error));
    } finally {
      setLoginPending(false);
    }
  };

  const submitCommitment = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setFormError("");
    setSaving(true);
    const payload: CommitmentInput = {
      ...form,
      title: form.title.trim(),
      description: form.description?.trim() || null,
    };
    try {
      const saved = editing
        ? await updateCommitment(editing.id, payload)
        : await createCommitment(payload);
      setCommitments((current) =>
        sortCommitments(
          editing
            ? current.map((item) => (item.id === saved.id ? saved : item))
            : [...current, saved],
        ),
      );
      setModalOpen(false);
    } catch (error) {
      setFormError(errorMessage(error));
    } finally {
      setSaving(false);
    }
  };

  const removeCommitment = async (commitment: Commitment) => {
    if (!window.confirm(`Delete “${commitment.title}”? This cannot be undone.`)) {
      return;
    }
    setBusyId(commitment.id);
    setPageError("");
    try {
      await deleteCommitment(commitment.id);
      setCommitments((current) =>
        current.filter((item) => item.id !== commitment.id),
      );
    } catch (error) {
      setPageError(errorMessage(error));
    } finally {
      setBusyId(null);
    }
  };

  const toggleCompletion = async (commitment: Commitment) => {
    setBusyId(commitment.id);
    setPageError("");
    try {
      const updated = await setCommitmentCompletion(
        commitment.id,
        !commitment.completed,
      );
      setCommitments((current) =>
        sortCommitments(
          current.map((item) => (item.id === updated.id ? updated : item)),
        ),
      );
    } catch (error) {
      setPageError(errorMessage(error));
    } finally {
      setBusyId(null);
    }
  };

  const signOut = async () => {
    setLoggingOut(true);
    setPageError("");
    try {
      await logout();
      setUser(null);
      setCommitments([]);
    } catch (error) {
      setPageError(errorMessage(error));
    } finally {
      setLoggingOut(false);
    }
  };

  if (authChecking) {
    return (
      <main className="auth-loading" aria-live="polite">
        <span className="brand-mark">S</span>
        <span className="spinner" />
        <p>Checking your Studyflow session…</p>
      </main>
    );
  }

  if (!user) {
    return (
      <main className="login-page">
        <section className="login-intro">
          <a className="brand" href="/" aria-label="Studyflow home">
            <span className="brand-mark">S</span>
            <span>studyflow</span>
          </a>
          <div className="login-message">
            <span className="eyebrow">A little more organized</span>
            <h1>Make room for what matters.</h1>
            <p>
              Bring classes, work, and everything in between into one calm place.
            </p>
            <div className="login-art" aria-hidden="true">
              <div className="art-orbit orbit-one" />
              <div className="art-orbit orbit-two" />
              <div className="art-card">
                <span className="art-check">✓</span>
                <div>
                  <b>One thing at a time</b>
                  <small>Your next step is right here.</small>
                </div>
              </div>
              <span className="art-star star-one">✳</span>
              <span className="art-star star-two">✦</span>
            </div>
          </div>
          <p className="login-footer">A clearer day starts here.</p>
        </section>

        <section className="login-panel">
          <form className="login-form" onSubmit={submitLogin}>
            <span className="eyebrow">Welcome back</span>
            <h2>Sign in to Studyflow</h2>
            <p className="muted">Your commitments are waiting for you.</p>
            {pageError && <ErrorNotice message={pageError} />}
            {loginError && <ErrorNotice message={loginError} />}
            <label>
              Email address
              <input
                type="email"
                autoComplete="username"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@example.com"
                required
                autoFocus
              />
            </label>
            <label>
              Password
              <input
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Enter your password"
                required
              />
            </label>
            <button className="button button-primary login-submit" disabled={loginPending}>
              {loginPending ? <><span className="spinner spinner-light" /> Signing in…</> : "Sign in"}
            </button>
            <p className="login-note">
              Use your Studyflow demo account to continue.
            </p>
          </form>
        </section>
      </main>
    );
  }

  const incompleteCount = commitments.filter((item) => !item.completed).length;
  const completedCount = commitments.length - incompleteCount;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="/" aria-label="Studyflow home">
          <span className="brand-mark">S</span>
          <span>studyflow</span>
        </a>
        <div className="sidebar-label">YOUR SPACE</div>
        <button
          className={`nav-item ${filter === "all" ? "active" : ""}`}
          onClick={() => setFilter("all")}
        >
          <span className="nav-icon">▦</span> All commitments
          <span className="nav-count">{commitments.length}</span>
        </button>
        <button
          className={`nav-item ${filter === "upcoming" ? "active" : ""}`}
          onClick={() => setFilter("upcoming")}
        >
          <span className="nav-icon">◷</span> Upcoming
        </button>
        <button
          className={`nav-item ${filter === "completed" ? "active" : ""}`}
          onClick={() => setFilter("completed")}
        >
          <span className="nav-icon">✓</span> Completed
        </button>
        <div className="sidebar-tip">
          <span className="tip-icon">✦</span>
          <strong>Small steps count.</strong>
          <p>Keep showing up for the things you care about.</p>
        </div>
        <div className="profile">
          <div className="avatar">{user.email.charAt(0).toUpperCase()}</div>
          <div className="profile-details">
            <strong>{user.email.split("@")[0]}</strong>
            <span>{user.email}</span>
          </div>
          <button
            className="icon-button logout-button"
            onClick={() => void signOut()}
            disabled={loggingOut}
            aria-label="Sign out"
            title="Sign out"
          >
            ↗
          </button>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="mobile-brand brand">
            <span className="brand-mark">S</span>
            <span>studyflow</span>
          </div>
          <div className="today-label">{new Intl.DateTimeFormat(undefined, { weekday: "long", month: "long", day: "numeric" }).format(new Date())}</div>
          <button
            className="button button-primary add-button"
            onClick={openNewCommitment}
          >
            <span className="button-plus">+</span> Add commitment
          </button>
        </header>

        <section className="welcome-row">
          <div>
            <span className="eyebrow">YOUR PLANNER</span>
            <h1>Good to see you, {user.email.split("@")[0]}.</h1>
            <p>Keep your plans in view and take today one step at a time.</p>
          </div>
          <div className="welcome-decoration" aria-hidden="true">
            <span>✳</span><i /><b />
          </div>
        </section>

        {pageError && <ErrorNotice message={pageError} onClose={() => setPageError("")} />}

        <section className="summary-grid" aria-label="Commitment summary">
          <SummaryCard label="On your list" value={commitments.length} accent="lavender" icon="▦" />
          <SummaryCard label="Still to do" value={incompleteCount} accent="peach" icon="◷" />
          <SummaryCard label="Done and dusted" value={completedCount} accent="mint" icon="✓" />
        </section>

        <section className="commitments-section">
          <div className="section-heading">
            <div>
              <span className="eyebrow">YOUR COMMITMENTS</span>
              <h2>{filter === "all" ? "Everything, in one place" : filter === "upcoming" ? "Coming up" : "Look what you did"}</h2>
            </div>
            <div className="filter-tabs" aria-label="Filter commitments">
              {(["all", "upcoming", "completed"] as const).map((option) => (
                <button
                  key={option}
                  className={filter === option ? "selected" : ""}
                  onClick={() => setFilter(option)}
                >
                  {option === "all" ? "All" : option === "upcoming" ? "Upcoming" : "Completed"}
                </button>
              ))}
            </div>
          </div>

          {loadingCommitments ? (
            <div className="state-card" aria-live="polite">
              <span className="spinner" />
              <p>Gathering your commitments…</p>
            </div>
          ) : visibleCommitments.length === 0 ? (
            <EmptyState filter={filter} onAdd={openNewCommitment} />
          ) : (
            <div className="commitment-list">
              {visibleCommitments.map((commitment) => (
                <article
                  className={`commitment-card ${commitment.completed ? "is-complete" : ""}`}
                  key={commitment.id}
                >
                  <button
                    className={`completion-toggle ${commitment.completed ? "checked" : ""}`}
                    onClick={() => void toggleCompletion(commitment)}
                    disabled={busyId === commitment.id}
                    aria-label={commitment.completed ? "Mark incomplete" : "Mark complete"}
                    title={commitment.completed ? "Mark incomplete" : "Mark complete"}
                  >
                    {commitment.completed ? "✓" : ""}
                  </button>
                  <div className={`type-icon type-${commitment.type}`}>
                    {TYPE_ICONS[commitment.type]}
                  </div>
                  <div className="commitment-main">
                    <div className="commitment-title-row">
                      <h3>{commitment.title}</h3>
                      {commitment.completed && <span className="done-pill">Done</span>}
                    </div>
                    {commitment.description && (
                      <p className="commitment-description">{commitment.description}</p>
                    )}
                    <div className="commitment-meta">
                      <span className={`type-pill pill-${commitment.type}`}>{TYPE_LABELS[commitment.type]}</span>
                      <span><span className="meta-symbol">▦</span>{formatDate(commitment.date)}</span>
                      <span><span className="meta-symbol">◷</span>{formatTime(commitment.start_time, commitment.end_time)}</span>
                    </div>
                  </div>
                  <div className="card-actions">
                    <button
                      className="icon-button"
                      onClick={() => openEditCommitment(commitment)}
                      aria-label={`Edit ${commitment.title}`}
                      title="Edit"
                    >
                      ✎
                    </button>
                    <button
                      className="icon-button delete-action"
                      onClick={() => void removeCommitment(commitment)}
                      disabled={busyId === commitment.id}
                      aria-label={`Delete ${commitment.title}`}
                      title="Delete"
                    >
                      {busyId === commitment.id ? "…" : "×"}
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
        <footer className="page-footer">One step at a time. You’ve got this.</footer>
      </main>

      {modalOpen && (
        <div className="modal-backdrop" onMouseDown={(event) => {
          if (event.target === event.currentTarget && !saving) setModalOpen(false);
        }}>
          <section
            className="commitment-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="commitment-modal-title"
          >
            <div className="modal-heading">
              <div>
                <span className="eyebrow">{editing ? "MAKE A CHANGE" : "ADD TO YOUR PLANNER"}</span>
                <h2 id="commitment-modal-title">{editing ? "Edit commitment" : "A new commitment"}</h2>
              </div>
              <button
                className="icon-button modal-close"
                onClick={() => setModalOpen(false)}
                disabled={saving}
                aria-label="Close"
              >
                ×
              </button>
            </div>
            <form className="commitment-form" onSubmit={submitCommitment}>
              {formError && <ErrorNotice message={formError} />}
              <label className="form-full">
                What do you need to do?
                <input
                  autoFocus
                  maxLength={200}
                  value={form.title}
                  onChange={(event) => setForm({ ...form, title: event.target.value })}
                  placeholder="e.g. Finish biology lab"
                  required
                />
              </label>
              <label>
                Type
                <select
                  value={form.type}
                  onChange={(event) => setForm({ ...form, type: event.target.value as CommitmentType })}
                >
                  {Object.entries(TYPE_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
              </label>
              <label>
                Date
                <input
                  type="date"
                  value={form.date}
                  onChange={(event) => setForm({ ...form, date: event.target.value })}
                  required
                />
              </label>
              <label>
                Start time <span className="optional-label">Optional</span>
                <input
                  type="time"
                  value={form.start_time ?? ""}
                  onChange={(event) => setForm({ ...form, start_time: event.target.value || null })}
                />
              </label>
              <label>
                End time <span className="optional-label">Optional</span>
                <input
                  type="time"
                  value={form.end_time ?? ""}
                  onChange={(event) => setForm({ ...form, end_time: event.target.value || null })}
                />
              </label>
              <label className="form-full">
                Notes <span className="optional-label">Optional</span>
                <textarea
                  rows={3}
                  maxLength={5000}
                  value={form.description ?? ""}
                  onChange={(event) => setForm({ ...form, description: event.target.value || null })}
                  placeholder="Add a few helpful details…"
                />
              </label>
              <div className="form-actions form-full">
                <button
                  type="button"
                  className="button button-quiet"
                  onClick={() => setModalOpen(false)}
                  disabled={saving}
                >
                  Cancel
                </button>
                <button className="button button-primary" disabled={saving}>
                  {saving ? "Saving…" : editing ? "Save changes" : "Add commitment"}
                </button>
              </div>
            </form>
          </section>
        </div>
      )}
    </div>
  );
}

function SummaryCard({
  label,
  value,
  accent,
  icon,
}: {
  label: string;
  value: number;
  accent: string;
  icon: string;
}) {
  return (
    <div className="summary-card">
      <div>
        <span className="summary-label">{label}</span>
        <strong>{value}</strong>
      </div>
      <span className={`summary-icon ${accent}`}>{icon}</span>
    </div>
  );
}

function EmptyState({
  filter,
  onAdd,
}: {
  filter: "all" | "upcoming" | "completed";
  onAdd: () => void;
}) {
  const isFirst = filter === "all";
  return (
    <div className="empty-state">
      <div className="empty-illustration" aria-hidden="true">
        <span>✓</span>
        <i />
        <b />
      </div>
      <h3>{isFirst ? "Your planner is a blank canvas." : filter === "upcoming" ? "Nothing coming up just yet." : "No completed commitments here yet."}</h3>
      <p>{isFirst ? "Add your first commitment and give your plans a home." : "When there’s something to show, you’ll find it here."}</p>
      {isFirst && (
        <button className="button button-primary" onClick={onAdd}>
          <span className="button-plus">+</span> Add your first commitment
        </button>
      )}
    </div>
  );
}

function ErrorNotice({
  message,
  onClose,
}: {
  message: string;
  onClose?: () => void;
}) {
  return (
    <div className="error-notice" role="alert">
      <span className="error-mark">!</span>
      <span>{message}</span>
      {onClose && (
        <button className="error-close" onClick={onClose} aria-label="Dismiss error">×</button>
      )}
    </div>
  );
}

function errorMessage(error: unknown) {
  return error instanceof Error
    ? error.message
    : "Something went wrong. Please try again.";
}

export default App;
