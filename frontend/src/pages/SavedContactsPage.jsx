import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Textarea } from '../components/ui/textarea';
import { BookmarkSimple, Copy, EnvelopeSimple, Phone, LinkedinLogo, Buildings, NotePencil, Trash, Check, X } from '@phosphor-icons/react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

const SavedContactsPage = () => {
  const navigate = useNavigate();
  const [contacts, setContacts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingNoteId, setEditingNoteId] = useState(null);
  const [noteText, setNoteText] = useState('');
  const [savingNote, setSavingNote] = useState(false);

  useEffect(() => {
    fetchContacts();
  }, []);

  const fetchContacts = async () => {
    try {
      const res = await axios.get(`${API}/api/contacts`, { withCredentials: true });
      setContacts(res.data);
    } catch (error) {
      console.error('Failed to fetch contacts', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveContact = async (contactId) => {
    if (!window.confirm('Remove this contact from your saved list?')) return;
    try {
      await axios.delete(`${API}/api/contacts/${contactId}`, { withCredentials: true });
      setContacts(prev => prev.filter(c => c.id !== contactId));
      toast.success('Contact removed');
    } catch (error) {
      toast.error('Failed to remove contact');
    }
  };

  const handleEditNote = (contact) => {
    setEditingNoteId(contact.id);
    setNoteText(contact.note || '');
  };

  const handleSaveNote = async (contactId) => {
    setSavingNote(true);
    try {
      await axios.put(`${API}/api/contacts/${contactId}/note`, { note: noteText }, { withCredentials: true });
      setContacts(prev => prev.map(c => c.id === contactId ? { ...c, note: noteText } : c));
      setEditingNoteId(null);
      toast.success('Note saved');
    } catch (error) {
      toast.error('Failed to save note');
    } finally {
      setSavingNote(false);
    }
  };

  const copyToClipboard = (text, label) => {
    navigator.clipboard.writeText(text);
    toast.success(`${label} copied`);
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
        <div className="mb-8">
          <h1 className="font-['Playfair_Display'] text-3xl text-white mb-2 flex items-center gap-3">
            <BookmarkSimple size={32} weight="duotone" className="text-[#D4AF37]" />
            Saved Contacts
          </h1>
          <p className="text-white/60">Keep track of the connections that matter</p>
        </div>

        {/* Contacts List */}
        {contacts.length === 0 ? (
          <div className="text-center py-16 bg-[#121621] border border-white/5 rounded-sm">
            <img 
              src="https://images.pexels.com/photos/13337440/pexels-photo-13337440.png?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940" 
              alt="No contacts"
              className="w-32 h-32 object-contain mx-auto mb-6 opacity-50"
            />
            <h3 className="font-['Playfair_Display'] text-xl text-white mb-2">No saved contacts yet</h3>
            <p className="text-white/60 mb-6">Start saving contacts from event directories</p>
            <Button
              onClick={() => navigate('/events')}
              className="bg-[#D4AF37] text-[#0A0D14]"
            >
              Browse Events
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            {contacts.map((contact, index) => (
              <div
                key={contact.id}
                className="bg-[#121621] border border-white/5 p-6 rounded-sm hover:border-[#D4AF37]/30 transition-all animate-fade-in"
                style={{ animationDelay: `${index * 50}ms` }}
                data-testid={`contact-card-${contact.id}`}
              >
                <div className="flex flex-col lg:flex-row gap-6">
                  {/* Avatar & Basic Info */}
                  <div className="flex gap-4 flex-1">
                    <div className="w-16 h-16 rounded-sm overflow-hidden bg-[#0A0D14] flex-shrink-0">
                      {contact.profile_photo ? (
                        <img
                          src={`${API}/api/files/${contact.profile_photo}`}
                          alt={contact.name}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center bg-[#D4AF37]/20">
                          <span className="font-['Playfair_Display'] text-xl text-[#D4AF37]">
                            {contact.name?.charAt(0)?.toUpperCase()}
                          </span>
                        </div>
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <Link 
                        to={`/profile/${contact.id}`}
                        className="font-['Playfair_Display'] text-lg text-white hover:text-[#D4AF37] transition-colors block"
                      >
                        {contact.name}
                      </Link>
                      {contact.role_title && (
                        <p className="text-white/60 text-sm">{contact.role_title}</p>
                      )}
                      {contact.company && (
                        <p className="text-white/40 text-sm flex items-center gap-1">
                          <Buildings size={14} weight="duotone" />
                          {contact.company}
                        </p>
                      )}
                      {contact.looking_for && (
                        <p className="text-white/60 text-sm mt-2 line-clamp-2">
                          <span className="text-[#D4AF37]">Looking for:</span> {contact.looking_for}
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Contact Actions */}
                  <div className="flex items-start gap-2 flex-shrink-0">
                    {contact.email && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => copyToClipboard(contact.email, 'Email')}
                        className="text-white/60 hover:text-white hover:bg-white/5"
                        title={contact.email}
                      >
                        <EnvelopeSimple size={18} />
                      </Button>
                    )}
                    {contact.phone && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => copyToClipboard(contact.phone, 'Phone')}
                        className="text-white/60 hover:text-white hover:bg-white/5"
                        title={contact.phone}
                      >
                        <Phone size={18} />
                      </Button>
                    )}
                    {contact.linkedin_url && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => window.open(contact.linkedin_url, '_blank')}
                        className="text-white/60 hover:text-white hover:bg-white/5"
                      >
                        <LinkedinLogo size={18} />
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleEditNote(contact)}
                      className="text-white/60 hover:text-[#D4AF37] hover:bg-[#D4AF37]/10"
                      title="Add/Edit Note"
                    >
                      <NotePencil size={18} />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleRemoveContact(contact.id)}
                      className="text-white/60 hover:text-red-400 hover:bg-red-500/10"
                      title="Remove"
                    >
                      <Trash size={18} />
                    </Button>
                  </div>
                </div>

                {/* Note Section */}
                {editingNoteId === contact.id ? (
                  <div className="mt-4 pt-4 border-t border-white/5 space-y-3">
                    <Textarea
                      value={noteText}
                      onChange={(e) => setNoteText(e.target.value)}
                      placeholder="Add a private note about this contact..."
                      className="bg-[#0A0D14] border-white/10 text-white resize-none"
                      rows={3}
                      autoFocus
                    />
                    <div className="flex gap-2">
                      <Button
                        onClick={() => handleSaveNote(contact.id)}
                        disabled={savingNote}
                        className="bg-[#D4AF37] text-[#0A0D14] font-medium px-4 py-2 rounded-sm hover:bg-[#F0C84B]"
                      >
                        {savingNote ? 'Saving...' : (
                          <>
                            <Check size={16} className="mr-2" />
                            Save
                          </>
                        )}
                      </Button>
                      <Button
                        onClick={() => setEditingNoteId(null)}
                        variant="ghost"
                        className="text-white/60 hover:text-white"
                      >
                        <X size={16} className="mr-2" />
                        Cancel
                      </Button>
                    </div>
                  </div>
                ) : contact.note ? (
                  <div className="mt-4 pt-4 border-t border-white/5">
                    <p className="text-white/60 text-sm">
                      <span className="text-[#D4AF37] font-medium">Note:</span> {contact.note}
                    </p>
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default SavedContactsPage;
