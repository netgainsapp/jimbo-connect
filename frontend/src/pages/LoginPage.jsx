import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';
import { Label } from '../components/ui/label';
import { EnvelopeSimple, Lock, Eye, EyeSlash } from '@phosphor-icons/react';

const LoginPage = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = location.state?.from?.pathname || '/events';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    const result = await login(email, password);
    setLoading(false);

    if (result.success) {
      navigate(from, { replace: true });
    } else {
      setError(result.error);
    }
  };

  return (
    <div className="min-h-screen bg-[#0A0D14] flex items-center justify-center px-6 py-24">
      <div className="w-full max-w-md">
        <div className="text-center mb-12 animate-fade-in">
          <Link to="/" className="inline-block mb-8">
            <div className="w-14 h-14 bg-[#D4AF37] rounded-sm flex items-center justify-center mx-auto">
              <span className="font-['Playfair_Display'] font-bold text-[#0A0D14] text-2xl">J</span>
            </div>
          </Link>
          <h1 className="font-['Playfair_Display'] text-3xl sm:text-4xl text-white mb-3">
            Welcome Back
          </h1>
          <p className="text-white/60">Sign in to continue building your network</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6 animate-fade-in stagger-1" data-testid="login-form">
          {error && (
            <div className="bg-red-500/10 border border-red-500/20 text-red-400 px-4 py-3 rounded-sm text-sm" data-testid="login-error">
              {error}
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="email" className="text-white/80">Email</Label>
            <div className="relative">
              <EnvelopeSimple size={20} weight="duotone" className="absolute left-4 top-1/2 -translate-y-1/2 text-white/40" />
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="bg-[#0A0D14] border-white/10 text-white pl-12 h-12 rounded-sm focus:border-[#D4AF37] focus:ring-1 focus:ring-[#D4AF37]"
                required
                data-testid="login-email"
              />
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="password" className="text-white/80">Password</Label>
              <Link to="/forgot-password" className="text-sm text-[#D4AF37] hover:text-[#F0C84B] transition-colors">
                Forgot password?
              </Link>
            </div>
            <div className="relative">
              <Lock size={20} weight="duotone" className="absolute left-4 top-1/2 -translate-y-1/2 text-white/40" />
              <Input
                id="password"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
                className="bg-[#0A0D14] border-white/10 text-white pl-12 pr-12 h-12 rounded-sm focus:border-[#D4AF37] focus:ring-1 focus:ring-[#D4AF37]"
                required
                data-testid="login-password"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-white/40 hover:text-white/60 transition-colors"
              >
                {showPassword ? <EyeSlash size={20} /> : <Eye size={20} />}
              </button>
            </div>
          </div>

          <Button
            type="submit"
            disabled={loading}
            className="w-full bg-[#D4AF37] text-[#0A0D14] font-medium h-12 rounded-sm hover:bg-[#F0C84B] transition-all disabled:opacity-50"
            data-testid="login-submit"
          >
            {loading ? 'Signing in...' : 'Sign In'}
          </Button>

          <p className="text-center text-white/60 text-sm">
            Don't have an account?{' '}
            <Link to="/register" className="text-[#D4AF37] hover:text-[#F0C84B] transition-colors">
              Create one
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
};

export default LoginPage;
