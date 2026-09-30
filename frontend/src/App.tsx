import { useEffect, useState } from 'react';
import { Link, Navigate, Route, Routes, useLocation, useNavigate, useParams } from 'react-router-dom';
import api from './services/api';
import type { DocumentItem, ProgressOverview, QuizDetail, QuizItem, QuizSubmissionResult, StudyAnswer, User } from './types';

const getUserFromStorage = (): User | null => {
  const raw = localStorage.getItem('ai_studymate_user');
  if (!raw) return null;
  try {
    return JSON.parse(raw) as User;
  } catch {
    return null;
  }
};

function App() {
  const [user, setUser] = useState<User | null>(getUserFromStorage());
  const location = useLocation();

  const isAuthenticated = Boolean(user);
  const currentPath = location.pathname;

  const handleLogin = (nextUser: User) => {
    setUser(nextUser);
    localStorage.setItem('ai_studymate_user', JSON.stringify(nextUser));
  };

  const handleLogout = () => {
    setUser(null);
    localStorage.removeItem('ai_studymate_user');
    localStorage.removeItem('ai_studymate_token');
  };

  useEffect(() => {
    const token = localStorage.getItem('ai_studymate_token');
    if (!token || !user) {
      return;
    }

    api.get('/auth/me')
      .then((response) => {
        const nextUser = response.data as User;
        setUser(nextUser);
        localStorage.setItem('ai_studymate_user', JSON.stringify(nextUser));
      })
      .catch(() => {
        handleLogout();
      });
  }, [user?.id]);

  return (
    <div className="min-h-screen bg-slate-100 text-slate-800">
      {isAuthenticated ? (
        <Shell user={user} onLogout={handleLogout} currentPath={currentPath}>
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/login" element={<Navigate to="/dashboard" replace />} />
            <Route path="/register" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<DashboardPage user={user} />} />
            <Route path="/documents" element={<DocumentsPage />} />
            <Route path="/documents/:id" element={<DocumentDetailPage />} />
            <Route path="/study" element={<StudyPage />} />
            <Route path="/quizzes" element={<QuizListPage />} />
            <Route path="/quiz/new" element={<QuizListPage />} />
            <Route path="/quiz/:id" element={<QuizPage />} />
            <Route path="/result/:id" element={<ResultPage />} />
            <Route path="/progress" element={<ProgressPage />} />
          </Routes>
        </Shell>
      ) : (
        <Routes>
          <Route path="/login" element={<LoginPage onLogin={handleLogin} />} />
          <Route path="/register" element={<RegisterPage onLogin={handleLogin} />} />
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      )}
    </div>
  );
}

function Shell({
  children,
  user,
  onLogout,
  currentPath,
}: {
  children: React.ReactNode;
  user: User | null;
  onLogout: () => void;
  currentPath: string;
}) {
  const navItems = [
    { label: 'Dashboard', path: '/dashboard' },
    { label: 'Documents', path: '/documents' },
    { label: 'Study', path: '/study' },
    { label: 'Quizzes', path: '/quizzes' },
    { label: 'Progress', path: '/progress' },
  ];

  return (
    <div>
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <div>
            <Link to="/dashboard" className="text-xl font-bold text-indigo-700">AI StudyMate</Link>
          </div>
          <nav className="hidden gap-5 md:flex">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={currentPath.startsWith(item.path) ? 'font-semibold text-indigo-700' : 'text-slate-600'}
              >
                {item.label}
              </Link>
            ))}
          </nav>
          <div className="flex items-center gap-3">
            <span className="text-sm text-slate-600">{user?.name}</span>
            <button onClick={onLogout} className="rounded bg-slate-800 px-3 py-1.5 text-white">Logout</button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
    </div>
  );
}

function LoginPage({ onLogin }: { onLogin: (user: User) => void }) {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    try {
      const response = await api.post('/auth/login', { email, password });
      const token = response.data.access_token;
      const user = response.data.user as User;
      localStorage.setItem('ai_studymate_token', token);
      onLogin(user);
      navigate('/dashboard');
    } catch (error: unknown) {
      setError(error instanceof Error ? error.message : 'Login failed');
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-lg">
        <h1 className="mb-4 text-2xl font-bold">Welcome back</h1>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium">Email</label>
            <input value={email} onChange={(e) => setEmail(e.target.value)} className="w-full rounded border p-2" required />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="w-full rounded border p-2" required />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button type="submit" className="w-full rounded bg-indigo-600 py-2 font-medium text-white">Login</button>
        </form>
        <p className="mt-4 text-sm text-slate-600">
          Need an account? <Link to="/register" className="text-indigo-600">Register</Link>
        </p>
      </div>
    </div>
  );
}

function RegisterPage({ onLogin }: { onLogin: (user: User) => void }) {
  const navigate = useNavigate();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');
    try {
      const response = await api.post('/auth/register', { name, email, password });
      const token = response.data.access_token;
      const user = response.data.user as User;
      localStorage.setItem('ai_studymate_token', token);
      onLogin(user);
      navigate('/dashboard');
    } catch (error: unknown) {
      setError(error instanceof Error ? error.message : 'Registration failed');
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-lg">
        <h1 className="mb-4 text-2xl font-bold">Create your account</h1>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium">Name</label>
            <input value={name} onChange={(e) => setName(e.target.value)} className="w-full rounded border p-2" required />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Email</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="w-full rounded border p-2" required />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="w-full rounded border p-2" required />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button type="submit" className="w-full rounded bg-indigo-600 py-2 font-medium text-white">Register</button>
        </form>
        <p className="mt-4 text-sm text-slate-600">
          Already have an account? <Link to="/login" className="text-indigo-600">Login</Link>
        </p>
      </div>
    </div>
  );
}

function DashboardPage({ user }: { user: User | null }) {
  const [documents, setDocuments] = useState<DocumentItem[] | null>(null);
  const [quizzes, setQuizzes] = useState<QuizItem[] | null>(null);
  const [progress, setProgress] = useState<ProgressOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [errors, setErrors] = useState<string[]>([]);

  useEffect(() => {
    const loadDashboard = async () => {
      const results = await Promise.allSettled([
        api.get('/documents'),
        api.get('/quizzes'),
        api.get('/progress'),
      ]);
      const nextErrors: string[] = [];
      if (results[0].status === 'fulfilled') setDocuments(results[0].value.data as DocumentItem[]);
      else nextErrors.push(results[0].reason instanceof Error ? results[0].reason.message : 'Documents could not be loaded.');
      if (results[1].status === 'fulfilled') setQuizzes(results[1].value.data as QuizItem[]);
      else nextErrors.push(results[1].reason instanceof Error ? results[1].reason.message : 'Quizzes could not be loaded.');
      if (results[2].status === 'fulfilled') setProgress(results[2].value.data as ProgressOverview);
      else nextErrors.push(results[2].reason instanceof Error ? results[2].reason.message : 'Progress could not be loaded.');
      setErrors(nextErrors);
      setLoading(false);
    };
    void loadDashboard();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">Your study overview</h1>
        <div className="flex gap-2">
          <Link to="/documents" className="rounded border border-slate-300 px-4 py-2 font-medium">Documents</Link>
          <Link to="/quizzes" className="rounded bg-indigo-600 px-4 py-2 font-medium text-white">Open quizzes</Link>
        </div>
      </div>
      {errors.length > 0 && <div role="alert" className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-800">{errors.join(' ')}</div>}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Welcome" value={user?.name ?? 'Student'} />
        <StatCard label="Documents" value={loading ? 'Loading' : documents === null ? 'Unavailable' : String(documents.length)} />
        <StatCard label="Quizzes" value={loading ? 'Loading' : quizzes === null ? 'Unavailable' : String(quizzes.length)} />
        <StatCard label="Overall accuracy" value={progress ? `${progress.overall_accuracy}%` : loading ? 'Loading' : 'Unavailable'} />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card">
          <h2 className="mb-4 text-lg font-semibold">Recent study activity</h2>
          {progress?.recent_attempts?.length ? (
            <ul className="space-y-2 text-sm text-slate-600">
              {progress.recent_attempts.slice(0, 5).map((attempt, index) => (
                <li key={`${attempt.quiz_id}-${attempt.submitted_at}-${index}`} className="rounded bg-slate-50 p-2">
                  <span className="font-medium">Quiz #{attempt.quiz_id}</span> · {attempt.score}% · {attempt.correct_answers}/{attempt.total_questions} correct
                  <time className="mt-1 block text-xs text-slate-500">{new Date(attempt.submitted_at).toLocaleString()}</time>
                </li>
              ))}
            </ul>
          ) : progress ? (
            <p className="text-sm text-slate-500">No quiz attempts yet.</p>
          ) : <p className="text-sm text-slate-500">Activity is unavailable.</p>}
        </div>
        <div className="card">
          <div className="mb-4 flex items-baseline justify-between">
            <h2 className="text-lg font-semibold">Progress summary</h2>
            <Link to="/progress" className="text-sm font-medium text-indigo-700">View progress</Link>
          </div>
          {progress?.weak_topics.length ? (
            <ul className="space-y-2 text-sm text-slate-600">
              {progress.weak_topics.map((topic) => <li key={topic} className="rounded bg-amber-50 p-2">Needs practice: {topic}</li>)}
            </ul>
          ) : progress ? (
            <p className="text-sm text-slate-500">No weak topics in your recorded quiz history.</p>
          ) : (
            <p className="text-sm text-slate-500">Progress is unavailable.</p>
          )}
        </div>
      </div>
    </div>
  );
}

function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [message, setMessage] = useState<{ text: string; isError: boolean } | null>(null);
  const [loadError, setLoadError] = useState('');
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);

  const loadDocuments = async () => {
    try {
      const response = await api.get('/documents');
      setDocuments(response.data as DocumentItem[]);
      setLoadError('');
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : 'Documents could not be loaded.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  const uploadDocument = async () => {
    if (!selectedFile) return;
    setUploading(true);
    setMessage(null);
    const formData = new FormData();
    formData.append('file', selectedFile);
    try {
      const response = await api.post('/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      const document = response.data as DocumentItem;
      setMessage({ text: `${document.filename}: ${document.status}.`, isError: document.status === 'FAILED' });
      setSelectedFile(null);
      await loadDocuments();
    } catch (error) {
      setMessage({ text: error instanceof Error ? error.message : 'Upload failed.', isError: true });
      await loadDocuments();
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="card">
          <h1 className="mb-3 text-xl font-semibold">Upload document</h1>
        <div className="flex flex-col gap-3 md:flex-row">
          <input type="file" accept=".pdf,.docx,.txt" onChange={(e) => setSelectedFile(e.target.files?.[0] ?? null)} className="flex-1" />
            <button onClick={uploadDocument} disabled={!selectedFile || uploading} className="rounded bg-indigo-600 px-4 py-2 text-white disabled:opacity-50">{uploading ? 'Uploading...' : 'Upload'}</button>
        </div>
        <p className="text-sm text-slate-500">PDF, DOCX, or TXT · maximum 8 MB</p>
        {message && <p role={message.isError ? 'alert' : 'status'} className={`mt-3 text-sm ${message.isError ? 'text-red-700' : 'text-emerald-700'}`}>{message.text}</p>}
      </div>

      <div className="card">
        <h2 className="mb-4 text-xl font-semibold">Your documents</h2>
        {loadError && <p role="alert" className="mb-3 text-sm text-red-700">{loadError}</p>}
        <div className="space-y-3">
          {documents.length ? documents.map((document) => (
            <div key={document.id} className="flex items-center justify-between rounded border p-3">
              <div>
                <Link to={`/documents/${document.id}`} className="font-medium text-indigo-700">{document.filename}</Link>
                <p className={`text-sm ${document.status === 'FAILED' ? 'text-red-700' : 'text-slate-500'}`}>{document.status} · {document.content_type}</p>
                {document.error && <p role="alert" className="mt-1 text-sm text-red-700">{document.error}</p>}
              </div>
              <div className="text-sm text-slate-600">{document.file_size} bytes</div>
            </div>
          )) : loading ? <p className="text-slate-500">Loading documents...</p> : !loadError ? <p className="text-slate-500">No documents uploaded yet.</p> : null}
        </div>
      </div>
    </div>
  );
}

function DocumentDetailPage() {
  const { id } = useParams();
  const [document, setDocument] = useState<DocumentItem | null>(null);
  const [summary, setSummary] = useState('');
  const [error, setError] = useState('');
  const [summaryError, setSummaryError] = useState('');
  const [summaryLoading, setSummaryLoading] = useState(false);

  useEffect(() => {
    if (!id) return;
    setDocument(null);
    setSummary('');
    setError('');
    setSummaryError('');
    api.get(`/documents/${id}`).then((response) => {
      const item = response.data as DocumentItem;
      setDocument(item);
    }).catch((loadError) => setError(loadError instanceof Error ? loadError.message : 'Document could not be loaded.'));
  }, [id]);

  const generateSummary = async () => {
    if (!id || document?.status !== 'READY') return;
    setSummaryLoading(true);
    setSummaryError('');
    try {
      const response = await api.post(`/documents/${id}/summary`);
      setSummary(response.data.summary as string);
    } catch (summaryFailure) {
      setSummaryError(summaryFailure instanceof Error ? summaryFailure.message : 'Summary generation failed. No summary was generated.');
    } finally {
      setSummaryLoading(false);
    }
  };

  return (
    <div className="card space-y-4">
      {error && <p role="alert" className="text-red-700">{error}</p>}
      <h1 className="text-2xl font-bold">{document?.filename ?? 'Document'}</h1>
      <p className={document?.status === 'FAILED' ? 'text-sm font-medium text-red-700' : 'text-sm text-slate-600'}>Status: {document?.status ?? (error ? 'Unavailable' : 'Loading...')}</p>
      {document?.error && <p role="alert" className="text-sm text-red-700">{document.error}</p>}
      <div className="rounded bg-slate-50 p-4">
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
          <h2 className="font-semibold">Summary</h2>
          <button type="button" onClick={generateSummary} disabled={document?.status !== 'READY' || summaryLoading} className="rounded border border-slate-300 px-3 py-1.5 text-sm font-medium disabled:opacity-50">
            {summaryLoading ? 'Generating...' : summary ? 'Regenerate summary' : 'Generate summary'}
          </button>
        </div>
        {summaryError ? <p role="alert" className="whitespace-pre-wrap text-red-700">{summaryError}</p> : <p className="whitespace-pre-wrap text-slate-700">{summary || 'No summary generated yet.'}</p>}
      </div>
      {document?.status === 'READY' && <Link to="/study" className="inline-block rounded bg-indigo-600 px-4 py-2 font-medium text-white">Ask about this document</Link>}
    </div>
  );
}

function StudyPage() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState('');
  const [question, setQuestion] = useState('');
  const [result, setResult] = useState<StudyAnswer | null>(null);
  const [documentError, setDocumentError] = useState('');
  const [error, setError] = useState('');
  const [loadingDocuments, setLoadingDocuments] = useState(true);
  const [asking, setAsking] = useState(false);

  useEffect(() => {
    api.get('/documents').then((response) => {
      const readyDocuments = (response.data as DocumentItem[]).filter((document) => document.status === 'READY');
      setDocuments(readyDocuments);
      if (readyDocuments[0]) setSelectedDocumentId(String(readyDocuments[0].id));
    }).catch((loadError) => setDocumentError(loadError instanceof Error ? loadError.message : 'Documents could not be loaded.'))
      .finally(() => setLoadingDocuments(false));
  }, []);

  const askQuestion = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!selectedDocumentId || !question.trim()) return;
    setAsking(true);
    setError('');
    setResult(null);
    try {
      const response = await api.post('/study/ask', { document_id: Number(selectedDocumentId), question });
      setResult(response.data as StudyAnswer);
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Question failed. No answer was generated.');
    } finally {
      setAsking(false);
    }
  };

  return (
    <div className="space-y-6">
      <form onSubmit={askQuestion} className="card space-y-4">
        <h1 className="text-xl font-semibold">Study assistant</h1>
        {documentError && <p role="alert" className="text-sm text-red-700">{documentError}</p>}
        <label className="block space-y-1 text-sm font-medium">
          <span>Document</span>
          <select value={selectedDocumentId} onChange={(event) => setSelectedDocumentId(event.target.value)} disabled={loadingDocuments || documents.length === 0} className="w-full rounded border p-2">
            {documents.map((doc) => <option key={doc.id} value={doc.id}>{doc.filename}</option>)}
          </select>
        </label>
        {!loadingDocuments && !documentError && documents.length === 0 && <p className="text-sm text-slate-600">No processed documents are available. Upload and process a document first.</p>}
        <label className="block space-y-1 text-sm font-medium">
          <span>Question</span>
          <textarea value={question} onChange={(event) => setQuestion(event.target.value)} className="w-full rounded border p-2" rows={4} placeholder="Ask a question about the selected document..." />
        </label>
        <button type="submit" disabled={asking || loadingDocuments || !selectedDocumentId || !question.trim()} className="rounded bg-indigo-600 px-4 py-2 font-medium text-white disabled:opacity-50">{asking ? 'Checking the document...' : 'Ask'}</button>
      </form>

      <div className="card">
        <h3 className="mb-2 text-lg font-semibold">Answer</h3>
        {error ? <p role="alert" className="whitespace-pre-wrap text-red-700">{error}</p> : result ? <p className="whitespace-pre-wrap text-slate-700">{result.answer}</p> : <p className="text-slate-500">No answer yet.</p>}
        {result?.sources.length ? (
          <div className="mt-4">
            <h4 className="font-semibold">Sources</h4>
            <ul className="ml-5 list-disc text-sm text-slate-600">
              {result.sources.map((source, index) => (
                <li key={`${source.document_id}-${source.filename}-${source.page}-${index}`}>{source.filename}{source.page !== null ? ` · page ${source.page}` : ''}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function QuizListPage() {
  const navigate = useNavigate();
  const [quizzes, setQuizzes] = useState<QuizItem[]>([]);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [documentLoadError, setDocumentLoadError] = useState('');
  const [documentId, setDocumentId] = useState('');
  const [topic, setTopic] = useState('');
  const [difficulty, setDifficulty] = useState('medium');
  const [questionCount, setQuestionCount] = useState(5);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const loadQuizzes = async () => {
    try {
      const response = await api.get('/quizzes');
      setQuizzes(response.data as QuizItem[]);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Could not load quizzes.');
    }
  };

  useEffect(() => {
    loadQuizzes();
    api.get('/documents')
      .then((response) => {
        setDocuments(response.data as DocumentItem[]);
        setDocumentLoadError('');
      })
      .catch((loadError) => setDocumentLoadError(loadError instanceof Error ? loadError.message : 'Documents could not be loaded.'));
  }, []);

  const generateQuiz = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      const response = await api.post('/quizzes/generate', {
        document_id: documentId ? Number(documentId) : null,
        topic: topic.trim() || null,
        difficulty,
        question_count: questionCount,
      });
      navigate(`/quiz/${response.data.id}`);
    } catch (generationError) {
      setError(generationError instanceof Error ? generationError.message : 'Quiz generation failed.');
    } finally {
      setLoading(false);
    }
  };

  const generateAdaptiveQuiz = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await api.post('/quizzes/adaptive');
      navigate(`/quiz/${response.data.id}`);
    } catch (generationError) {
      setError(generationError instanceof Error ? generationError.message : 'Adaptive quiz generation failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="card space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-xl font-semibold">Create a quiz</h1>
          <button type="button" onClick={generateAdaptiveQuiz} disabled={loading} className="rounded border border-indigo-600 px-3 py-2 font-medium text-indigo-700 disabled:opacity-50">
            Generate adaptive quiz
          </button>
        </div>
        <form onSubmit={generateQuiz} className="grid gap-4 md:grid-cols-2">
          <label className="space-y-1 text-sm font-medium">
            <span>Source document</span>
            <select value={documentId} onChange={(event) => setDocumentId(event.target.value)} className="w-full rounded border p-2">
              <option value="">General study material</option>
              {documents.map((document) => <option key={document.id} value={document.id}>{document.filename}</option>)}
            </select>
            {documentLoadError && <span role="alert" className="block text-sm font-normal text-red-700">{documentLoadError}</span>}
          </label>
          <label className="space-y-1 text-sm font-medium">
            <span>Topic</span>
            <input value={topic} onChange={(event) => setTopic(event.target.value)} className="w-full rounded border p-2" placeholder="General" />
          </label>
          <label className="space-y-1 text-sm font-medium">
            <span>Difficulty</span>
            <select value={difficulty} onChange={(event) => setDifficulty(event.target.value)} className="w-full rounded border p-2">
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
            </select>
          </label>
          <label className="space-y-1 text-sm font-medium">
            <span>Questions</span>
            <input type="number" min={1} max={20} value={questionCount} onChange={(event) => setQuestionCount(Number(event.target.value))} className="w-full rounded border p-2" />
          </label>
          <div className="flex items-center gap-3 md:col-span-2">
            <button type="submit" disabled={loading} className="rounded bg-indigo-600 px-4 py-2 font-medium text-white disabled:opacity-50">
              {loading ? 'Generating...' : 'Generate quiz'}
            </button>
            {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
          </div>
        </form>
      </div>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Your quizzes</h2>
        {quizzes.length ? quizzes.map((quiz) => (
          <Link key={quiz.id} to={`/quiz/${quiz.id}`} className="flex flex-wrap items-center justify-between gap-2 rounded border border-slate-200 bg-white p-4 hover:border-indigo-400">
            <span className="font-medium">{quiz.title}</span>
            <span className="text-sm text-slate-600">{quiz.topic} · {quiz.difficulty} · {quiz.question_count} questions</span>
          </Link>
        )) : <p className="text-sm text-slate-500">No quizzes yet.</p>}
      </section>
    </div>
  );
}

function QuizPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [quiz, setQuiz] = useState<QuizDetail | null>(null);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    const loadQuiz = async () => {
      if (!id) return;
      setLoading(true);
      setMessage('');
      try {
        const response = await api.get(`/quizzes/${id}`);
        setQuiz(response.data as QuizDetail);
        setAnswers({});
      } catch (loadError) {
        setMessage(loadError instanceof Error ? loadError.message : 'Quiz could not be loaded.');
      } finally {
        setLoading(false);
      }
    };
    loadQuiz();
  }, [id]);

  const submitQuiz = async () => {
    if (!quiz || Object.keys(answers).length !== quiz.questions.length) {
      setMessage('Select one answer for every question before submitting.');
      return;
    }
    const quizId = Number(id);
    setSubmitting(true);
    setMessage('');
    try {
      const response = await api.post(`/quizzes/${quizId}/submit`, { quiz_id: quizId, answers });
      navigate(`/result/${quizId}`, { state: response.data });
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Quiz submission failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="card space-y-5">
      {loading ? <p>Loading quiz...</p> : null}
      {message && <p role="alert" className="text-red-700">{message}</p>}
      {quiz && (
        <>
          <div>
            <h1 className="text-xl font-semibold">{quiz.title}</h1>
            <p className="text-sm text-slate-600">{quiz.topic} · {quiz.difficulty}</p>
          </div>
          {quiz.questions.map((question, questionIndex) => (
            <fieldset key={question.id} className="space-y-3 border-t border-slate-200 pt-4">
              <legend className="font-medium">{questionIndex + 1}. {question.question}</legend>
              {question.options.map((option, optionIndex) => (
                <label key={`${question.id}-${optionIndex}`} className="flex cursor-pointer items-start gap-3 rounded border border-slate-200 p-3 hover:bg-slate-50">
                  <input
                    type="radio"
                    name={`question-${question.id}`}
                    value={optionIndex}
                    checked={answers[String(question.id)] === optionIndex}
                    onChange={() => setAnswers((current) => ({ ...current, [String(question.id)]: optionIndex }))}
                    className="mt-1"
                  />
                  <span>{option}</span>
                </label>
              ))}
            </fieldset>
          ))}
          <button onClick={submitQuiz} disabled={loading || submitting} className="rounded bg-indigo-600 px-4 py-2 font-medium text-white disabled:opacity-50">
            {submitting ? 'Submitting...' : 'Submit quiz'}
          </button>
        </>
      )}
    </div>
  );
}

function ResultPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const result = (location.state as QuizSubmissionResult | null) || null;

  return (
    <div className="card space-y-4">
      <h1 className="text-2xl font-bold">Quiz result</h1>
      {result ? (
        <>
          <div className="grid gap-3 sm:grid-cols-3">
            <StatCard label="Score" value={`${result.score}%`} />
            <StatCard label="Correct answers" value={`${result.correct_answers}/${result.total_questions}`} />
            <StatCard label="Overall percentage" value={`${result.percentage}%`} />
          </div>
          <section className="space-y-3">
            <h2 className="text-lg font-semibold">Answer review</h2>
            {result.question_results.map((item, index) => (
              <article key={item.question_id} className="rounded border border-slate-200 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h3 className="font-medium">{index + 1}. {item.question}</h3>
                  <span className={item.is_correct ? 'text-sm font-semibold text-emerald-700' : 'text-sm font-semibold text-red-700'}>{item.is_correct ? 'Correct' : 'Incorrect'}</span>
                </div>
                <p className="mt-2 text-sm text-slate-600">Your answer: {item.selected_answer === null ? 'No answer' : item.options[item.selected_answer] ?? 'Invalid option'}</p>
                {!item.is_correct && <p className="text-sm text-slate-600">Correct answer: {item.options[item.correct_answer]}</p>}
                {item.explanation && <p className="mt-2 text-sm text-slate-700">{item.explanation}</p>}
                <p className="mt-2 text-xs text-slate-500">Topic: {item.topic}</p>
              </article>
            ))}
          </section>
          <section className="space-y-3">
            <h2 className="text-lg font-semibold">Topic performance</h2>
            {Object.entries(result.topic_performance).length ? Object.entries(result.topic_performance).map(([topic, performance]) => (
              <div key={topic} className="flex flex-wrap justify-between gap-2 rounded bg-slate-50 p-3 text-sm">
                <span className="font-medium">{topic}</span>
                <span>{performance.accuracy}% · {performance.status} · {performance.attempts} attempts</span>
              </div>
            )) : <p className="text-sm text-slate-500">No topic performance was recorded.</p>}
          </section>
        </>
      ) : (
        <p role="status">No submitted result is available in this session.</p>
      )}
      <button onClick={() => navigate('/dashboard')} className="rounded bg-slate-800 px-4 py-2 text-white">Back to dashboard</button>
    </div>
  );
}

function ProgressPage() {
  const [progress, setProgress] = useState<ProgressOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get('/progress')
      .then((response) => setProgress(response.data as ProgressOverview))
      .catch((loadError) => setError(loadError instanceof Error ? loadError.message : 'Progress could not be loaded.'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h1 className="text-2xl font-semibold">Progress</h1>
        {progress && <p className="text-sm text-slate-600">Based on {progress.total_quizzes} attempted quizzes · average score {progress.average_score}%</p>}
      </div>
      {error && <p role="alert" className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</p>}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Overall accuracy" value={progress ? `${progress.overall_accuracy}%` : loading ? 'Loading' : 'Unavailable'} />
        <StatCard label="Strong topics" value={progress ? String(progress.strong_topics.length) : loading ? 'Loading' : 'Unavailable'} />
        <StatCard label="Normal topics" value={progress ? String(progress.normal_topics.length) : loading ? 'Loading' : 'Unavailable'} />
        <StatCard label="Weak topics" value={progress ? String(progress.weak_topics.length) : loading ? 'Loading' : 'Unavailable'} />
      </div>

      <div className="card">
        <h2 className="mb-4 text-xl font-semibold">Performance by topic</h2>
        {progress?.topic_performance.length ? <div className="space-y-3">
          {progress.topic_performance.map((row) => {
            const statusStyle = row.status === 'STRONG'
              ? 'bg-emerald-100 text-emerald-800'
              : row.status === 'WEAK'
                ? 'bg-rose-100 text-rose-800'
                : 'bg-sky-100 text-sky-800';
            return (
              <div key={row.topic} className="rounded border border-slate-200 p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-medium">{row.topic}</span>
                  <span className={`rounded px-2 py-1 text-xs font-semibold ${statusStyle}`}>{row.status}</span>
                </div>
                <p className="mt-2 text-sm text-slate-600">Accuracy: {row.accuracy}% · Latest score: {row.latest_score}% · {row.attempts} attempts · {row.correct_answers}/{row.total_questions} correct</p>
              </div>
            );
          })}
        </div> : progress ? <p className="text-sm text-slate-500">Complete a quiz to see topic performance.</p> : loading ? <p className="text-sm text-slate-500">Loading topic performance...</p> : null}
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="card">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-bold">{value}</p>
    </div>
  );
}

export default App;
