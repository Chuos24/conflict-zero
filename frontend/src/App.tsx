import { Routes, Route, Navigate } from 'react-router-dom';
import { Dashboard } from './pages/Dashboard';
import { ConflictDetail } from './pages/ConflictDetail';
import { ConflictForm } from './pages/ConflictForm';
import { Layout } from './components/Layout';

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/conflicts/new" element={<ConflictForm />} />
        <Route path="/conflicts/:id" element={<ConflictDetail />} />
        <Route path="/conflicts/:id/edit" element={<ConflictForm />} />
      </Routes>
    </Layout>
  );
}

export default App;
