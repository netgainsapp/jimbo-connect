import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { CheckCircle, XCircle } from '@phosphor-icons/react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

const JoinEventPage = () => {
  const { code } = useParams();
  const navigate = useNavigate();
  const { user, loading: authLoading } = useAuth();
  const [joining, setJoining] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [eventInfo, setEventInfo] = useState(null);

  useEffect(() => {
    if (!authLoading && !user) {
      // Redirect to login with return path
      navigate(`/login?redirect=/join/${code}`);
    }
  }, [user, authLoading, navigate, code]);

  useEffect(() => {
    if (user && code && !success && !error) {
      handleJoin();
    }
  }, [user, code]);

  const handleJoin = async () => {
    setJoining(true);
    try {
      const res = await axios.post(`${API}/api/events/join/${code}`, {}, { withCredentials: true });
      setSuccess(true);
      setEventInfo(res.data);
      toast.success(`Joined "${res.data.name}" successfully!`);
      // Redirect to event after a short delay
      setTimeout(() => {
        navigate(`/event/${res.data.event_id}`);
      }, 2000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to join event');
    } finally {
      setJoining(false);
    }
  };

  if (authLoading) {
    return (
      <div className="min-h-screen bg-[#0A0D14] flex items-center justify-center">
        <div className="w-12 h-12 border-2 border-[#D4AF37] border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0A0D14] flex items-center justify-center px-6">
      <div className="max-w-md w-full text-center">
        {joining && (
          <div className="animate-fade-in">
            <div className="w-16 h-16 border-2 border-[#D4AF37] border-t-transparent rounded-full animate-spin mx-auto mb-6"></div>
            <h1 className="font-['Playfair_Display'] text-2xl text-white mb-2">Joining Event...</h1>
            <p className="text-white/60">Please wait while we add you to the event.</p>
          </div>
        )}

        {success && eventInfo && (
          <div className="animate-fade-in">
            <CheckCircle size={64} weight="duotone" className="text-green-400 mx-auto mb-6" />
            <h1 className="font-['Playfair_Display'] text-2xl text-white mb-2">You're In!</h1>
            <p className="text-white/60 mb-6">
              You've successfully joined <span className="text-[#D4AF37]">{eventInfo.name}</span>
            </p>
            <p className="text-white/40 text-sm">Redirecting to the event directory...</p>
          </div>
        )}

        {error && (
          <div className="animate-fade-in">
            <XCircle size={64} weight="duotone" className="text-red-400 mx-auto mb-6" />
            <h1 className="font-['Playfair_Display'] text-2xl text-white mb-2">Unable to Join</h1>
            <p className="text-white/60 mb-6">{error}</p>
            <Button
              onClick={() => navigate('/events')}
              className="bg-[#D4AF37] text-[#0A0D14] font-medium px-6 py-3 rounded-sm hover:bg-[#F0C84B]"
            >
              Go to My Events
            </Button>
          </div>
        )}
      </div>
    </div>
  );
};

export default JoinEventPage;
