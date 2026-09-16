import { useState } from 'react';
import { request } from '../api';
import Icon from './Icon';

export default function Auth({ onAuthenticated }) {
  const [register, setRegister] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [sample, setSample] = useState(false);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState('');
  async function submit(e) {
    e.preventDefault();
    setError('');
    if (register && password !== confirmation) {
      setError('The passwords do not match.');
      return;
    }
    setWorking(true);
    try {
      const result = await request(`/auth/${register ? 'register' : 'login'}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password, ...(register ? { sample } : {}) }),
      });
      onAuthenticated(result);
    } catch (e) {
      setError(e.message);
    } finally {
      setWorking(false);
    }
  }
  return (
    <main className="auth-page">
      <div className="auth-brand">
        <Icon name="document" size={25} />
        <span>Feedback review</span>
      </div>
      <section className="auth-card">
        <span className="section-number">YOUR FEEDBACK WORKSPACE</span>
        <h1>{register ? 'Create your account' : 'Welcome back'}</h1>
        <p>
          {register
            ? 'A private workspace for your feedback, analysis and saved reports.'
            : 'Sign in to open your dashboard and report history.'}
        </p>
        <form onSubmit={submit}>
          <label className="field">
            Username
            <input
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              minLength={3}
              maxLength={40}
              pattern="[A-Za-z0-9][A-Za-z0-9._\-]{2,39}"
              autoCapitalize="none"
              spellCheck={false}
            />
          </label>
          <label className="field">
            Password
            <input
              type="password"
              autoComplete={register ? 'new-password' : 'current-password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={12}
              maxLength={128}
              required
            />
          </label>
          {register && (
            <>
              <small>Use at least 12 characters. No email address is needed.</small>
              <label className="field">
                Confirm password
                <input
                  type="password"
                  autoComplete="new-password"
                  value={confirmation}
                  onChange={(e) => setConfirmation(e.target.value)}
                  minLength={12}
                  maxLength={128}
                  required
                />
              </label>
              <label className="confirmation">
                <input
                  type="checkbox"
                  checked={sample}
                  onChange={(e) => setSample(e.target.checked)}
                />
                Start with a copy of the included sample feedback
              </label>
              <small>
                Leave this unchecked to start with an empty workspace for your own data.
              </small>
            </>
          )}
          {error && (
            <div className="error" role="alert">
              {error}
            </div>
          )}
          <button className="button auth-submit" disabled={working}>
            {working ? 'Please wait…' : register ? 'Create account' : 'Sign in'}
            <Icon name="arrow" size={16} />
          </button>
        </form>
        <div className="auth-switch">
          <span>{register ? 'Already have an account?' : 'New here?'}</span>
          <button
            className="inline-link"
            onClick={() => {
              setRegister(!register);
              setPassword('');
              setConfirmation('');
              setError('');
            }}
          >
            {register ? 'Sign in' : 'Create an account'}
          </button>
        </div>
      </section>
      <p className="auth-note">
        Your dashboard and saved reports are visible only to your account.
      </p>
    </main>
  );
}
