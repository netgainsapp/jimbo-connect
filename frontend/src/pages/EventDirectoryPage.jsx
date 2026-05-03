import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';
import { MagnifyingGlass, Funnel, BookmarkSimple, Buildings, MapPin, Users, ArrowLeft, X, EnvelopeSimple, Phone, LinkedinLogo } from '@phosphor-icons/react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

const EventDirectoryPage = () => {
  const { eventId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [event, setEvent] = useState(null);
  const [attendees, setAttendees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [industryFilter, setIndustryFilter] = useState('');
  const [tableFilter, setTableFilter] = useState('');
  const [savedContacts, setSavedContacts] = useState(new Set());

  const fetchEvent = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/api/events/${eventId}`, { withCredentials: true });
      setEvent(res.data);
    } catch (error) {
      toast.error('Event not found');
      navigate('/events');
    }
  }, [eventId, navigate]);

  const fetchAttendees = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (search) params.append('search', search);
      if (industryFilter && industryFilter !== 'all') params.append('industry', industryFilter);
      if (tableFilter && tableFilter !== 'all') params.append('table_cohort', tableFilter);
      
      const res = await axios.get(`${API}/api/events/${eventId}/attendees?${params}`, { withCredentials: true });
      setAttendees(res.data);
    } catch (error) {
      console.error('Failed to fetch attendees', error);
    }
  }, [eventId, search, industryFilter, tableFilter]);

  const fetchSavedContacts = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/api/contacts`, { withCredentials: true });
      setSavedContacts(new Set(res.data.map(c => c.id)));
    } catch (error) {
      console.error('Failed to fetch saved contacts', error);
    }
  }, []);

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await fetchEvent();
      await fetchAttendees();
      await fetchSavedContacts();
      setLoading(false);
    };
    loadData();
  }, [fetchEvent, fetchAttendees, fetchSavedContacts]);

  useEffect(() => {
    const debounce = setTimeout(() => {
      fetchAttendees();
    }, 300);
    return () => clearTimeout(debounce);
  }, [search, industryFilter, tableFilter, fetchAttendees]);

  const handleSaveContact = async (contactUserId) => {
    try {
      if (savedContacts.has(contactUserId)) {
        await axios.delete(`${API}/api/contacts/${contactUserId}`, { withCredentials: true });
        setSavedContacts(prev => {
          const newSet = new Set(prev);
          newSet.delete(contactUserId);
          return newSet;
        });
        toast.success('Contact removed');
      } else {
        await axios.post(`${API}/api/contacts/save`, { contact_user_id: contactUserId }, { withCredentials: true });
        setSavedContacts(prev => new Set([...prev, contactUserId]));
        toast.success('Contact saved');
      }
    } catch (error) {
      toast.error('Failed to update contact');
    }
  };

  const copyToClipboard = (text, label) => {
    navigator.clipboard.writeText(text);
    toast.success(`${label} copied`);
  };

  // Get unique industries and tables from attendees
  const uniqueIndustries = [...new Set(attendees.filter(a => a.industry).map(a => a.industry))];
  const uniqueTables = [...new Set(attendees.filter(a => a.table_cohort).map(a => a.table_cohort))];

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
        {/* Back button */}
        <button
          onClick={() => navigate('/events')}
          className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors mb-6"
          data-testid="back-to-events"
        >
          <ArrowLeft size={20} />
          Back to Events
        </button>

        {/* Event Header */}
        <div className="mb-8">
          <h1 className="text-3xl sm:text-4xl font-semibold text-foreground mb-2">{event?.name}</h1>
          <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
            {event?.date && (
              <span className="flex items-center gap-1">
                {event.date}
              </span>
            )}
            {event?.location && (
              <span className="flex items-center gap-1">
                <MapPin size={16} weight="duotone" />
                {event.location}
              </span>
            )}
            <span className="flex items-center gap-1">
              <Users size={16} weight="duotone" />
              {attendees.length} attendees
            </span>
          </div>
        </div>

        {/* Search & Filters */}
        <div className="flex flex-col sm:flex-row gap-4 mb-8">
          <div className="relative flex-1">
            <MagnifyingGlass size={20} className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by name, company, role, or what they're looking for..."
              className="pl-12 h-12 rounded-full"
              data-testid="search-input"
            />
            {search && (
              <button
                onClick={() => setSearch('')}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                <X size={18} />
              </button>
            )}
          </div>
          
          <div className="flex gap-2">
            <Select value={industryFilter} onValueChange={setIndustryFilter}>
              <SelectTrigger className="w-[180px]" data-testid="industry-filter">
                <Funnel size={16} className="mr-2" />
                <SelectValue placeholder="Industry" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Industries</SelectItem>
                {uniqueIndustries.map(ind => (
                  <SelectItem key={ind} value={ind}>{ind}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            {uniqueTables.length > 0 && (
              <Select value={tableFilter} onValueChange={setTableFilter}>
                <SelectTrigger className="w-[180px]" data-testid="table-filter">
                  <SelectValue placeholder="Table/Cohort" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Tables</SelectItem>
                  {uniqueTables.map(table => (
                    <SelectItem key={table} value={table}>{table}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>
        </div>

        {/* Attendees Grid */}
        {attendees.length === 0 ? (
          <div className="text-center py-16">
            <div className="w-16 h-16 bg-muted rounded-full flex items-center justify-center mx-auto mb-6">
              <Users size={32} className="text-muted-foreground" />
            </div>
            <h3 className="text-xl font-semibold text-foreground mb-2">No attendees found</h3>
            <p className="text-muted-foreground">Try adjusting your search or filters</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {attendees.map((attendee, index) => (
              <div
                key={attendee.id}
                className="bg-card border border-border p-6 rounded-lg hover:border-primary/30 transition-all group animate-fade-in"
                style={{ animationDelay: `${index * 50}ms` }}
                data-testid={`attendee-card-${attendee.id}`}
              >
                <div className="flex gap-4">
                  {/* Avatar */}
                  <div className="w-20 h-20 rounded-lg overflow-hidden bg-muted flex-shrink-0">
                    {attendee.profile_photo ? (
                      <img
                        src={`${API}/api/files/${attendee.profile_photo}`}
                        alt={attendee.name}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center bg-primary/10">
                        <span className="text-2xl font-semibold text-primary">
                          {attendee.name?.charAt(0)?.toUpperCase()}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <Link 
                      to={`/profile/${attendee.id}`}
                      className="text-lg font-semibold text-foreground hover:text-primary transition-colors block truncate"
                    >
                      {attendee.name}
                    </Link>
                    {attendee.role_title && (
                      <p className="text-muted-foreground text-sm truncate">{attendee.role_title}</p>
                    )}
                    {attendee.company && (
                      <p className="text-muted-foreground/70 text-sm flex items-center gap-1 truncate">
                        <Buildings size={14} weight="duotone" />
                        {attendee.company}
                      </p>
                    )}
                  </div>
                </div>

                {/* Looking for */}
                {attendee.looking_for && (
                  <p className="text-muted-foreground text-sm mt-4 line-clamp-2">
                    <span className="text-primary font-medium">Looking for:</span> {attendee.looking_for}
                  </p>
                )}

                {/* Tags */}
                <div className="flex flex-wrap gap-2 mt-4">
                  {attendee.industry && (
                    <span className="bg-muted text-foreground text-xs px-3 py-1 rounded-full">
                      {attendee.industry}
                    </span>
                  )}
                  {attendee.table_cohort && (
                    <span className="bg-primary/10 text-primary text-xs px-3 py-1 rounded-full">
                      {attendee.table_cohort}
                    </span>
                  )}
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 mt-4 pt-4 border-t border-border">
                  {attendee.id !== user?.id && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleSaveContact(attendee.id)}
                      className={`flex-1 ${savedContacts.has(attendee.id) ? 'text-primary' : 'text-muted-foreground'} hover:text-primary hover:bg-primary/10`}
                      data-testid={`save-contact-${attendee.id}`}
                    >
                      <BookmarkSimple size={18} weight={savedContacts.has(attendee.id) ? 'fill' : 'duotone'} className="mr-2" />
                      {savedContacts.has(attendee.id) ? 'Saved' : 'Save'}
                    </Button>
                  )}
                  {attendee.email && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => copyToClipboard(attendee.email, 'Email')}
                      className="text-muted-foreground hover:text-foreground"
                      data-testid={`copy-contact-${attendee.id}`}
                    >
                      <EnvelopeSimple size={18} />
                    </Button>
                  )}
                  {attendee.phone && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => copyToClipboard(attendee.phone, 'Phone')}
                      className="text-muted-foreground hover:text-foreground"
                    >
                      <Phone size={18} />
                    </Button>
                  )}
                  {attendee.linkedin_url && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => window.open(attendee.linkedin_url, '_blank')}
                      className="text-muted-foreground hover:text-foreground"
                    >
                      <LinkedinLogo size={18} />
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default EventDirectoryPage;
