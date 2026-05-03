import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { CalendarBlank, MapPin, Users, Plus, Link as LinkIcon, Trash, PencilSimple, Eye, EyeSlash } from '@phosphor-icons/react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '../components/ui/dialog';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

const AdminPage = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [events, setEvents] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);
  const [editEvent, setEditEvent] = useState(null);
  
  // Form state
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    date: '',
    location: '',
    industries: '',
  });

  useEffect(() => {
    if (user?.role !== 'admin') {
      navigate('/');
      return;
    }
    fetchData();
  }, [user, navigate]);

  const fetchData = async () => {
    try {
      const [eventsRes, statsRes] = await Promise.all([
        axios.get(`${API}/api/events`, { withCredentials: true }),
        axios.get(`${API}/api/admin/stats`, { withCredentials: true }),
      ]);
      setEvents(eventsRes.data);
      setStats(statsRes.data);
    } catch (error) {
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        ...formData,
        industries: formData.industries ? formData.industries.split(',').map(i => i.trim()) : [],
      };
      await axios.post(`${API}/api/events`, payload, { withCredentials: true });
      toast.success('Event created successfully');
      setCreateOpen(false);
      resetForm();
      fetchData();
    } catch (error) {
      toast.error('Failed to create event');
    }
  };

  const handleUpdate = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        ...formData,
        industries: formData.industries ? formData.industries.split(',').map(i => i.trim()) : [],
      };
      await axios.put(`${API}/api/events/${editEvent.id}`, payload, { withCredentials: true });
      toast.success('Event updated successfully');
      setEditEvent(null);
      resetForm();
      fetchData();
    } catch (error) {
      toast.error('Failed to update event');
    }
  };

  const handleDelete = async (eventId) => {
    if (!window.confirm('Are you sure you want to delete this event?')) return;
    try {
      await axios.delete(`${API}/api/events/${eventId}`, { withCredentials: true });
      toast.success('Event deleted');
      fetchData();
    } catch (error) {
      toast.error('Failed to delete event');
    }
  };

  const toggleEventStatus = async (event) => {
    try {
      await axios.put(`${API}/api/events/${event.id}`, { is_active: !event.is_active }, { withCredentials: true });
      toast.success(event.is_active ? 'Event deactivated' : 'Event activated');
      fetchData();
    } catch (error) {
      toast.error('Failed to update event');
    }
  };

  const copyJoinLink = (code) => {
    const link = `${window.location.origin}/join/${code}`;
    navigator.clipboard.writeText(link);
    toast.success('Join link copied to clipboard');
  };

  const resetForm = () => {
    setFormData({ name: '', description: '', date: '', location: '', industries: '' });
  };

  const openEditDialog = (event) => {
    setFormData({
      name: event.name || '',
      description: event.description || '',
      date: event.date || '',
      location: event.location || '',
      industries: (event.industries || []).join(', '),
    });
    setEditEvent(event);
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
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-8">
          <div>
            <h1 className="text-3xl font-semibold text-foreground mb-2">Admin Dashboard</h1>
            <p className="text-muted-foreground">Manage your events and track engagement</p>
          </div>
          <Dialog open={createOpen} onOpenChange={setCreateOpen}>
            <DialogTrigger asChild>
              <Button 
                className="font-medium px-6 py-3 flex items-center gap-2"
                data-testid="create-event-btn"
              >
                <Plus size={20} weight="bold" />
                Create Event
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-md">
              <DialogHeader>
                <DialogTitle className="text-2xl font-semibold">Create New Event</DialogTitle>
                <DialogDescription>
                  Fill in the details below to create a new networking event.
                </DialogDescription>
              </DialogHeader>
              <form onSubmit={handleCreate} className="space-y-4 mt-4">
                <div className="space-y-2">
                  <Label>Event Name *</Label>
                  <Input
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="Tech Networking Night"
                    required
                    data-testid="event-name-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Date *</Label>
                  <Input
                    type="date"
                    value={formData.date}
                    onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                    required
                    data-testid="event-date-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Location</Label>
                  <Input
                    value={formData.location}
                    onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                    placeholder="San Francisco, CA"
                    data-testid="event-location-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Description</Label>
                  <Textarea
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    placeholder="Describe your event..."
                    className="resize-none"
                    rows={3}
                    data-testid="event-description-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Industries (comma separated)</Label>
                  <Input
                    value={formData.industries}
                    onChange={(e) => setFormData({ ...formData, industries: e.target.value })}
                    placeholder="Technology, Finance, Healthcare"
                    data-testid="event-industries-input"
                  />
                </div>
                <Button
                  type="submit"
                  className="w-full font-medium py-3"
                  data-testid="submit-event-btn"
                >
                  Create Event
                </Button>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            {[
              { label: 'Total Users', value: stats.total_users },
              { label: 'Total Events', value: stats.total_events },
              { label: 'Active Events', value: stats.active_events },
              { label: 'Connections Made', value: stats.total_connections },
            ].map((stat, i) => (
              <div key={i} className="bg-card border border-border p-6 rounded-lg">
                <p className="text-muted-foreground text-sm mb-1">{stat.label}</p>
                <p className="text-3xl font-semibold text-primary">{stat.value}</p>
              </div>
            ))}
          </div>
        )}

        {/* Events List */}
        <div className="space-y-4">
          <h2 className="text-xl font-semibold text-foreground">Events</h2>
          
          {events.length === 0 ? (
            <div className="bg-card border border-border p-12 rounded-lg text-center">
              <p className="text-muted-foreground mb-4">No events created yet</p>
              <Button onClick={() => setCreateOpen(true)}>
                Create Your First Event
              </Button>
            </div>
          ) : (
            <div className="grid gap-4">
              {events.map((event) => (
                <div
                  key={event.id}
                  className="bg-card border border-border p-6 rounded-lg hover:border-primary/30 transition-all"
                  data-testid={`event-card-${event.id}`}
                >
                  <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-xl font-semibold text-foreground">{event.name}</h3>
                        <span className={`text-xs px-2 py-1 rounded-full ${event.is_active ? 'bg-green-500/20 text-green-600 dark:text-green-400' : 'bg-muted text-muted-foreground'}`}>
                          {event.is_active ? 'Active' : 'Inactive'}
                        </span>
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
                    
                    <div className="flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => copyJoinLink(event.code)}
                        className="text-muted-foreground hover:text-foreground"
                        data-testid={`copy-link-${event.id}`}
                      >
                        <LinkIcon size={18} />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => navigate(`/event/${event.id}`)}
                        className="text-muted-foreground hover:text-foreground"
                        data-testid={`view-event-${event.id}`}
                      >
                        <Users size={18} />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => toggleEventStatus(event)}
                        className="text-muted-foreground hover:text-foreground"
                        data-testid={`toggle-event-${event.id}`}
                      >
                        {event.is_active ? <EyeSlash size={18} /> : <Eye size={18} />}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => openEditDialog(event)}
                        className="text-muted-foreground hover:text-foreground"
                        data-testid={`edit-event-${event.id}`}
                      >
                        <PencilSimple size={18} />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(event.id)}
                        className="text-destructive hover:text-destructive hover:bg-destructive/10"
                        data-testid={`delete-event-${event.id}`}
                      >
                        <Trash size={18} />
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Edit Dialog */}
        <Dialog open={!!editEvent} onOpenChange={(open) => !open && setEditEvent(null)}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle className="text-2xl font-semibold">Edit Event</DialogTitle>
              <DialogDescription>
                Update the event details below.
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={handleUpdate} className="space-y-4 mt-4">
              <div className="space-y-2">
                <Label>Event Name *</Label>
                <Input
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label>Date *</Label>
                <Input
                  type="date"
                  value={formData.date}
                  onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label>Location</Label>
                <Input
                  value={formData.location}
                  onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>Description</Label>
                <Textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="resize-none"
                  rows={3}
                />
              </div>
              <div className="space-y-2">
                <Label>Industries (comma separated)</Label>
                <Input
                  value={formData.industries}
                  onChange={(e) => setFormData({ ...formData, industries: e.target.value })}
                />
              </div>
              <Button
                type="submit"
                className="w-full font-medium py-3"
              >
                Update Event
              </Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
};

export default AdminPage;
