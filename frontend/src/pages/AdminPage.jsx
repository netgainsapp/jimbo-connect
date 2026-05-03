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
      <div className="min-h-screen bg-[#0A0D14] pt-24 flex items-center justify-center">
        <div className="w-12 h-12 border-2 border-[#D4AF37] border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0A0D14] pt-24 px-6 pb-12">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-8">
          <div>
            <h1 className="font-['Playfair_Display'] text-3xl text-white mb-2">Admin Dashboard</h1>
            <p className="text-white/60">Manage your events and track engagement</p>
          </div>
          <Dialog open={createOpen} onOpenChange={setCreateOpen}>
            <DialogTrigger asChild>
              <Button 
                className="bg-[#D4AF37] text-[#0A0D14] font-medium px-6 py-3 rounded-sm hover:bg-[#F0C84B] transition-all flex items-center gap-2"
                data-testid="create-event-btn"
              >
                <Plus size={20} weight="bold" />
                Create Event
              </Button>
            </DialogTrigger>
            <DialogContent className="bg-[#121621] border-white/10 text-white max-w-md">
              <DialogHeader>
                <DialogTitle className="font-['Playfair_Display'] text-2xl">Create New Event</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleCreate} className="space-y-4 mt-4">
                <div className="space-y-2">
                  <Label className="text-white/80">Event Name *</Label>
                  <Input
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="Tech Networking Night"
                    className="bg-[#0A0D14] border-white/10 text-white"
                    required
                    data-testid="event-name-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-white/80">Date *</Label>
                  <Input
                    type="date"
                    value={formData.date}
                    onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                    className="bg-[#0A0D14] border-white/10 text-white"
                    required
                    data-testid="event-date-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-white/80">Location</Label>
                  <Input
                    value={formData.location}
                    onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                    placeholder="San Francisco, CA"
                    className="bg-[#0A0D14] border-white/10 text-white"
                    data-testid="event-location-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-white/80">Description</Label>
                  <Textarea
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    placeholder="Describe your event..."
                    className="bg-[#0A0D14] border-white/10 text-white resize-none"
                    rows={3}
                    data-testid="event-description-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-white/80">Industries (comma separated)</Label>
                  <Input
                    value={formData.industries}
                    onChange={(e) => setFormData({ ...formData, industries: e.target.value })}
                    placeholder="Technology, Finance, Healthcare"
                    className="bg-[#0A0D14] border-white/10 text-white"
                    data-testid="event-industries-input"
                  />
                </div>
                <Button
                  type="submit"
                  className="w-full bg-[#D4AF37] text-[#0A0D14] font-medium py-3 rounded-sm hover:bg-[#F0C84B]"
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
              <div key={i} className="bg-[#121621] border border-white/5 p-6 rounded-sm">
                <p className="text-white/60 text-sm mb-1">{stat.label}</p>
                <p className="text-3xl font-['Playfair_Display'] text-[#D4AF37]">{stat.value}</p>
              </div>
            ))}
          </div>
        )}

        {/* Events List */}
        <div className="space-y-4">
          <h2 className="font-['Playfair_Display'] text-xl text-white">Events</h2>
          
          {events.length === 0 ? (
            <div className="bg-[#121621] border border-white/5 p-12 rounded-sm text-center">
              <p className="text-white/60 mb-4">No events created yet</p>
              <Button
                onClick={() => setCreateOpen(true)}
                className="bg-[#D4AF37] text-[#0A0D14]"
              >
                Create Your First Event
              </Button>
            </div>
          ) : (
            <div className="grid gap-4">
              {events.map((event) => (
                <div
                  key={event.id}
                  className="bg-[#121621] border border-white/5 p-6 rounded-sm hover:border-[#D4AF37]/30 transition-all"
                  data-testid={`event-card-${event.id}`}
                >
                  <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="font-['Playfair_Display'] text-xl text-white">{event.name}</h3>
                        <span className={`text-xs px-2 py-1 rounded-full ${event.is_active ? 'bg-green-500/20 text-green-400' : 'bg-white/10 text-white/60'}`}>
                          {event.is_active ? 'Active' : 'Inactive'}
                        </span>
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
                    
                    <div className="flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => copyJoinLink(event.code)}
                        className="text-white/60 hover:text-white hover:bg-white/5"
                        data-testid={`copy-link-${event.id}`}
                      >
                        <LinkIcon size={18} />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => navigate(`/event/${event.id}`)}
                        className="text-white/60 hover:text-white hover:bg-white/5"
                        data-testid={`view-event-${event.id}`}
                      >
                        <Users size={18} />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => toggleEventStatus(event)}
                        className="text-white/60 hover:text-white hover:bg-white/5"
                        data-testid={`toggle-event-${event.id}`}
                      >
                        {event.is_active ? <EyeSlash size={18} /> : <Eye size={18} />}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => openEditDialog(event)}
                        className="text-white/60 hover:text-white hover:bg-white/5"
                        data-testid={`edit-event-${event.id}`}
                      >
                        <PencilSimple size={18} />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(event.id)}
                        className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
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
          <DialogContent className="bg-[#121621] border-white/10 text-white max-w-md">
            <DialogHeader>
              <DialogTitle className="font-['Playfair_Display'] text-2xl">Edit Event</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleUpdate} className="space-y-4 mt-4">
              <div className="space-y-2">
                <Label className="text-white/80">Event Name *</Label>
                <Input
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="bg-[#0A0D14] border-white/10 text-white"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label className="text-white/80">Date *</Label>
                <Input
                  type="date"
                  value={formData.date}
                  onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                  className="bg-[#0A0D14] border-white/10 text-white"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label className="text-white/80">Location</Label>
                <Input
                  value={formData.location}
                  onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                  className="bg-[#0A0D14] border-white/10 text-white"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-white/80">Description</Label>
                <Textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="bg-[#0A0D14] border-white/10 text-white resize-none"
                  rows={3}
                />
              </div>
              <div className="space-y-2">
                <Label className="text-white/80">Industries (comma separated)</Label>
                <Input
                  value={formData.industries}
                  onChange={(e) => setFormData({ ...formData, industries: e.target.value })}
                  className="bg-[#0A0D14] border-white/10 text-white"
                />
              </div>
              <Button
                type="submit"
                className="w-full bg-[#D4AF37] text-[#0A0D14] font-medium py-3 rounded-sm hover:bg-[#F0C84B]"
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
