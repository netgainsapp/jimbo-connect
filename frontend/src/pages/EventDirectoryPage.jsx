import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';
import { MagnifyingGlass, Funnel, BookmarkSimple, Buildings, MapPin, Users, ArrowLeft, X, Copy, EnvelopeSimple, Phone, LinkedinLogo } from '@phosphor-icons/react';
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
      <div className="min-h-screen bg-[#0A0D14] pt-24 flex items-center justify-center">
        <div className="w-12 h-12 border-2 border-[#D4AF37] border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0A0D14] pt-24 px-6 pb-12">
      <div className="max-w-6xl mx-auto">
        {/* Back button */}
        <button
          onClick={() => navigate('/events')}
          className="flex items-center gap-2 text-white/60 hover:text-white transition-colors mb-6"
          data-testid="back-to-events"
        >
          <ArrowLeft size={20} />
          Back to Events
        </button>

        {/* Event Header */}
        <div className="mb-8">
          <h1 className="font-['Playfair_Display'] text-3xl sm:text-4xl text-white mb-2">{event?.name}</h1>
          <div className="flex flex-wrap gap-4 text-sm text-white/60">
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
            <MagnifyingGlass size={20} className="absolute left-4 top-1/2 -translate-y-1/2 text-white/40" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by name, company, role, or what they're looking for..."
              className="bg-white/5 border-white/10 text-white pl-12 h-12 rounded-full focus:border-white/30"
              data-testid="search-input"
            />
            {search && (
              <button
                onClick={() => setSearch('')}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-white/40 hover:text-white"
              >
                <X size={18} />
              </button>
            )}
          </div>
          
          <div className="flex gap-2">
            <Select value={industryFilter} onValueChange={setIndustryFilter}>
              <SelectTrigger className="w-[180px] bg-white/5 border-white/10 text-white" data-testid="industry-filter">
                <Funnel size={16} className="mr-2" />
                <SelectValue placeholder="Industry" />
              </SelectTrigger>
              <SelectContent className="bg-[#121621] border-white/10">
                <SelectItem value="all">All Industries</SelectItem>
                {uniqueIndustries.map(ind => (
                  <SelectItem key={ind} value={ind}>{ind}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            {uniqueTables.length > 0 && (
              <Select value={tableFilter} onValueChange={setTableFilter}>
                <SelectTrigger className="w-[180px] bg-white/5 border-white/10 text-white" data-testid="table-filter">
                  <SelectValue placeholder="Table/Cohort" />
                </SelectTrigger>
                <SelectContent className="bg-[#121621] border-white/10">
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
            <img 
              src="https://images.pexels.com/photos/13337440/pexels-photo-13337440.png?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940" 
              alt="No results"
              className="w-32 h-32 object-contain mx-auto mb-6 opacity-50"
            />
            <h3 className="font-['Playfair_Display'] text-xl text-white mb-2">No attendees found</h3>
            <p className="text-white/60">Try adjusting your search or filters</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {attendees.map((attendee, index) => (
              <div
                key={attendee.id}
                className="bg-[#121621] border border-white/5 p-6 rounded-sm hover:border-[#D4AF37]/30 transition-all group animate-fade-in"
                style={{ animationDelay: `${index * 50}ms` }}
                data-testid={`attendee-card-${attendee.id}`}
              >
                <div className="flex gap-4">
                  {/* Avatar */}
                  <div className="w-20 h-20 rounded-sm overflow-hidden bg-[#0A0D14] flex-shrink-0">
                    {attendee.profile_photo ? (
                      <img
                        src={`${API}/api/files/${attendee.profile_photo}`}
                        alt={attendee.name}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center bg-[#D4AF37]/20">
                        <span className="font-['Playfair_Display'] text-2xl text-[#D4AF37]">
                          {attendee.name?.charAt(0)?.toUpperCase()}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <Link 
                      to={`/profile/${attendee.id}`}
                      className="font-['Playfair_Display'] text-lg text-white hover:text-[#D4AF37] transition-colors block truncate"
                    >
                      {attendee.name}
                    </Link>
                    {attendee.role_title && (
                      <p className="text-white/60 text-sm truncate">{attendee.role_title}</p>
                    )}
                    {attendee.company && (
                      <p className="text-white/40 text-sm flex items-center gap-1 truncate">
                        <Buildings size={14} weight="duotone" />
                        {attendee.company}
                      </p>
                    )}
                  </div>
                </div>

                {/* Looking for */}
                {attendee.looking_for && (
                  <p className="text-white/60 text-sm mt-4 line-clamp-2">
                    <span className="text-[#D4AF37]">Looking for:</span> {attendee.looking_for}
                  </p>
                )}

                {/* Tags */}
                <div className="flex flex-wrap gap-2 mt-4">
                  {attendee.industry && (
                    <span className="bg-white/10 text-white text-xs px-3 py-1 rounded-full">
                      {attendee.industry}
                    </span>
                  )}
                  {attendee.table_cohort && (
                    <span className="bg-[#D4AF37]/20 text-[#D4AF37] text-xs px-3 py-1 rounded-full">
                      {attendee.table_cohort}
                    </span>
                  )}
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 mt-4 pt-4 border-t border-white/5">
                  {attendee.id !== user?.id && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleSaveContact(attendee.id)}
                      className={`flex-1 ${savedContacts.has(attendee.id) ? 'text-[#D4AF37]' : 'text-white/60'} hover:text-[#D4AF37] hover:bg-[#D4AF37]/10`}
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
                      className="text-white/60 hover:text-white hover:bg-white/5"
                      data-testid={`copy-email-${attendee.id}`}
                    >
                      <EnvelopeSimple size={18} />
                    </Button>
                  )}
                  {attendee.phone && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => copyToClipboard(attendee.phone, 'Phone')}
                      className="text-white/60 hover:text-white hover:bg-white/5"
                    >
                      <Phone size={18} />
                    </Button>
                  )}
                  {attendee.linkedin_url && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => window.open(attendee.linkedin_url, '_blank')}
                      className="text-white/60 hover:text-white hover:bg-white/5"
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
