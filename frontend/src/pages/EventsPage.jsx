import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { CalendarBlank, MapPin, Users, Link as LinkIcon, ArrowRight, Plus } from '@phosphor-icons/react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '../components/ui/dialog';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

const EventsPage = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [joinCode, setJoinCode] = useState('');
  const [joinDialogOpen, setJoinDialogOpen] = useState(false);
  const [joining, setJoining] = useState(false);

  useEffect(() => {
    fetchMyEvents();
  }, []);

  const fetchMyEvents = async () => {
    try {
      const res = await axios.get(`${API}/api/my-events`, { withCredentials: true });
      setEvents(res.data);
    } catch (error) {
      console.error('Failed to fetch events', error);
    } finally {
      setLoading(false);
    }
  };

  const handleJoinEvent = async (e) => {
    e.preventDefault();
    if (!joinCode.trim()) return;

    setJoining(true);
    try {
      const res = await axios.post(`${API}/api/events/join/${joinCode.trim()}`, {}, { withCredentials: true });
      toast.success(`Joined "${res.data.name}" successfully!`);
      setJoinDialogOpen(false);
      setJoinCode('');
      fetchMyEvents();
      navigate(`/event/${res.data.event_id}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to join event');
    } finally {
      setJoining(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0A0D14] pt-24 flex items-center justify-center">
        <div className="w-12 h-12 border-2 border-[#D4AF37] border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0A0D14] pt-24 px-6 pb-12">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-8">
          <div>
            <h1 className="font-['Playfair_Display'] text-3xl text-white mb-2">My Events</h1>
            <p className="text-white/60">Browse attendees and make connections</p>
          </div>
          <Dialog open={joinDialogOpen} onOpenChange={setJoinDialogOpen}>
            <DialogTrigger asChild>
              <Button 
                className="bg-[#D4AF37] text-[#0A0D14] font-medium px-6 py-3 rounded-sm hover:bg-[#F0C84B] transition-all flex items-center gap-2"
                data-testid="join-event-btn"
              >
                <Plus size={20} weight="bold" />
                Join Event
              </Button>
            </DialogTrigger>
            <DialogContent className="bg-[#121621] border-white/10 text-white max-w-md">
              <DialogHeader>
                <DialogTitle className="font-['Playfair_Display'] text-2xl">Join an Event</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleJoinEvent} className="space-y-4 mt-4">
                <div className="space-y-2">
                  <Label className="text-white/80">Event Code</Label>
                  <Input
                    value={joinCode}
                    onChange={(e) => setJoinCode(e.target.value)}
                    placeholder="Enter the event code or paste the link"
                    className="bg-[#0A0D14] border-white/10 text-white"
                    data-testid="join-code-input"
                  />
                  <p className="text-white/40 text-sm">
                    Enter the code shared by the event organizer
                  </p>
                </div>
                <Button
                  type="submit"
                  disabled={joining || !joinCode.trim()}
                  className="w-full bg-[#D4AF37] text-[#0A0D14] font-medium py-3 rounded-sm hover:bg-[#F0C84B] disabled:opacity-50"
                  data-testid="submit-join-btn"
                >
                  {joining ? 'Joining...' : 'Join Event'}
                </Button>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        {/* Events List */}
        {events.length === 0 ? (
          <div className="text-center py-16 bg-[#121621] border border-white/5 rounded-sm">
            <img 
              src="https://images.pexels.com/photos/13337440/pexels-photo-13337440.png?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940" 
              alt="No events"
              className="w-32 h-32 object-contain mx-auto mb-6 opacity-50"
            />
            <h3 className="font-['Playfair_Display'] text-xl text-white mb-2">No events yet</h3>
            <p className="text-white/60 mb-6">Join your first event to start networking</p>
            <Button
              onClick={() => setJoinDialogOpen(true)}
              className="bg-[#D4AF37] text-[#0A0D14]"
            >
              Join an Event
            </Button>
          </div>
        ) : (
          <div className="grid gap-4">
            {events.map((event, index) => (
              <Link
                key={event.id}
                to={`/event/${event.id}`}
                className="bg-[#121621] border border-white/5 p-6 rounded-sm hover:border-[#D4AF37]/30 transition-all group animate-fade-in block"
                style={{ animationDelay: `${index * 50}ms` }}
                data-testid={`event-link-${event.id}`}
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="font-['Playfair_Display'] text-xl text-white group-hover:text-[#D4AF37] transition-colors">
                        {event.name}
                      </h3>
                      {event.is_active && (
                        <span className="bg-green-500/20 text-green-400 text-xs px-2 py-1 rounded-full">
                          Active
                        </span>
                      )}
                    </div>
                    <div className="flex flex-wrap gap-4 text-sm text-white/60">
                      <span className="flex items-center gap-1">
                        <CalendarBlank size={16} weight="duotone" />
                        {event.date}
                      </span>
                      {event.location && (
                        <span className="flex items-center gap-1">
                          <MapPin size={16} weight="duotone" />
                          {event.location}
                        </span>
                      )}
                      <span className="flex items-center gap-1">
                        <Users size={16} weight="duotone" />
                        {event.attendee_count} attendees
                      </span>
                    </div>
                  </div>
                  <ArrowRight size={24} className="text-white/40 group-hover:text-[#D4AF37] group-hover:translate-x-1 transition-all" />
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default EventsPage;
