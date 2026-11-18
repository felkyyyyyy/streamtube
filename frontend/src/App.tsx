import React from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { Layout } from './components/Layout';
import { AuthProvider } from './context/AuthContext';
import { AuthPage } from './pages/AuthPage';
import { ChannelPage } from './pages/ChannelPage';
import { HomePage } from './pages/HomePage';
import { ModerationPage } from './pages/ModerationPage';
import { SearchPage } from './pages/SearchPage';
import { UploadPage } from './pages/UploadPage';
import { WatchPage } from './pages/WatchPage';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Layout>
          <Routes>
            <Route path="/" element={<HomePage feed="all" />} />
            <Route path="/subscriptions" element={<HomePage feed="subscriptions" />} />
            <Route path="/shared" element={<HomePage feed="shared" />} />
            <Route path="/studio" element={<HomePage feed="mine" />} />
            <Route path="/watch/:id" element={<WatchPage />} />
            <Route path="/channel/:handle" element={<ChannelPage />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/login" element={<AuthPage mode="login" />} />
            <Route path="/register" element={<AuthPage mode="register" />} />
            <Route path="/moderation" element={<ModerationPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Layout>
      </AuthProvider>
    </BrowserRouter>
  );
};

export default App;
