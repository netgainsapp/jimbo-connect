import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { CalendarBlank, MapPin, Users, ArrowRight, Plus } from '@phosphor-icons/react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
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
      <div className="min-h-screen bg-background pt-24 flex items-center justify-center">
        <div className="w-12 h-12 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background pt-24 px-6 pb-12">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-8">
          <div>
            <h1 className="text-3xl font-semibold text-foreground mb-2">My Events</h1>
            <p className="text-muted-foreground">Browse attendees and make connections</p>
          </div>
          <Dialog open={joinDialogOpen} onOpenChange={setJoinDialogOpen}>
            <DialogTrigger asChild>
              <Button 
                className="font-medium px-6 py-3 flex items-center gap-2"
                data-testid="join-event-btn"
              >
                <Plus size={20} weight="bold" />
                Join Event
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-md">
              <DialogHeader>
                <DialogTitle className="text-2xl font-semibold">Join an Event</DialogTitle>
                <DialogDescription>
                  Enter the event code shared by the organizer.
                </DialogDescription>
              </DialogHeader>
              <form onSubmit={handleJoinEvent} className="space-y-4 mt-4">
                <div className="space-y-2">
                  <Label>Event Code</Label>
                  <Input
                    value={joinCode}
                    onChange={(e) => setJoinCode(e.target.value)}
                    placeholder="Enter the event code or paste the link"
                    data-testid="join-code-input"
                  />
                  <p className="text-muted-foreground text-sm">
                    Enter the code shared by the event organizer
                  </p>
                </div>
                <Button
                  type="submit"
                  disabled={joining || !joinCode.trim()}
                  className="w-full font-medium py-3"
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
          <div className="text-center py-16 bg-card border border-border rounded-lg">
            <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mx-auto mb-6">
              <Users size={32} className="text-muted-foreground" />
            </div>
            <h3 className="text-xl font-semibold text-foreground mb-2">No events yet</h3>
            <p className="text-muted-foreground mb-6">Join your first event to start networking</p>
            <Button onClick={() => setJoinDialogOpen(true)}>
              Join an Event
            </Button>
          </div>
        ) : (
          <div className="grid gap-4">
            {events.map((event, index) => (
              <Link
                key={event.id}
                to={`/event/${event.id}`}
                className="bg-card border border-border p-6 rounded-lg hover:border-primary/30 transition-all group animate-fade-in block"
                style={{ animationDelay: `${index * 50}ms` }}
                data-testid={`event-link-${event.id}`}
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-xl font-semibold text-foreground group-hover:text-primary transition-colors">
                        {event.name}
                      </h3>
                      {event.is_active && (
                        <span className="bg-green-500/20 text-green-600 dark:text-green-400 text-xs px-2 py-1 rounded-full">
                          Active
                        </span>
                      )}
                    </div>
                    <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
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
                  <ArrowRight size={24} className="text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all" />
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
