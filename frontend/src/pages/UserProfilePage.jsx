import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Textarea } from '../components/ui/textarea';
import { 
  ArrowLeft, BookmarkSimple, Copy, EnvelopeSimple, Phone, LinkedinLogo, 
  Buildings, Briefcase, NotePencil, Check
} from '@phosphor-icons/react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

const UserProfilePage = () => {
  const { userId } = useParams();
  const navigate = useNavigate();
  const { user: currentUser } = useAuth();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isSaved, setIsSaved] = useState(false);
  const [note, setNote] = useState('');
  const [editingNote, setEditingNote] = useState(false);
  const [savingNote, setSavingNote] = useState(false);

  useEffect(() => {
    fetchUser();
    checkSavedStatus();
  }, [userId]);

  const fetchUser = async () => {
    try {
      const res = await axios.get(`${API}/api/profile/${userId}`, { withCredentials: true });
      setUser(res.data);
    } catch (error) {
      toast.error('User not found');
      navigate(-1);
    } finally {
      setLoading(false);
    }
  };

  const checkSavedStatus = async () => {
    try {
      const res = await axios.get(`${API}/api/contacts/${userId}/is-saved`, { withCredentials: true });
      setIsSaved(res.data.is_saved);
      setNote(res.data.note || '');
    } catch (error) {
      console.error('Failed to check saved status', error);
    }
  };

  const handleSaveContact = async () => {
    try {
      if (isSaved) {
        await axios.delete(`${API}/api/contacts/${userId}`, { withCredentials: true });
        setIsSaved(false);
        setNote('');
        toast.success('Contact removed');
      } else {
        await axios.post(`${API}/api/contacts/save`, { contact_user_id: userId }, { withCredentials: true });
        setIsSaved(true);
        toast.success('Contact saved');
      }
    } catch (error) {
      toast.error('Failed to update contact');
    }
  };

  const handleSaveNote = async () => {
    setSavingNote(true);
    try {
      await axios.put(`${API}/api/contacts/${userId}/note`, { note }, { withCredentials: true });
      setEditingNote(false);
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

  const copyAllInfo = () => {
    const info = [
      user.name,
      user.role_title && user.company ? `${user.role_title} at ${user.company}` : user.role_title || user.company,
      user.email,
      user.phone,
      user.linkedin_url,
    ].filter(Boolean).join('\n');
    navigator.clipboard.writeText(info);
    toast.success('Contact info copied');
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background pt-24 flex items-center justify-center">
        <div className="w-12 h-12 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (!user) return null;

  const isOwnProfile = currentUser?.id === userId;

  return (
    <div className="min-h-screen bg-background pt-24 px-6 pb-12">
      <div className="max-w-3xl mx-auto">
        {/* Back button */}
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors mb-6"
          data-testid="back-button"
        >
          <ArrowLeft size={20} />
          Back
        </button>

        {/* Profile Card */}
        <div className="bg-card border border-border rounded-lg overflow-hidden">
          {/* Header */}
          <div className="p-8 border-b border-border">
            <div className="flex flex-col sm:flex-row gap-6 items-start">
              {/* Avatar */}
              <div className="w-32 h-32 rounded-lg overflow-hidden bg-muted flex-shrink-0">
                {user.profile_photo ? (
                  <img
                    src={`${API}/api/files/${user.profile_photo}`}
                    alt={user.name}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center bg-primary/10">
                    <span className="text-4xl font-semibold text-primary">
                      {user.name?.charAt(0)?.toUpperCase()}
                    </span>
                  </div>
                )}
              </div>

              {/* Info */}
              <div className="flex-1">
                <h1 className="text-3xl font-semibold text-foreground mb-2">{user.name}</h1>
                {user.role_title && (
                  <p className="text-foreground/80 text-lg flex items-center gap-2 mb-1">
                    <Briefcase size={18} weight="duotone" className="text-primary" />
                    {user.role_title}
                  </p>
                )}
                {user.company && (
                  <p className="text-muted-foreground flex items-center gap-2 mb-1">
                    <Buildings size={18} weight="duotone" />
                    {user.company}
                  </p>
                )}
                {user.industry && (
                  <span className="inline-block bg-muted text-foreground text-sm px-3 py-1 rounded-full mt-2">
                    {user.industry}
                  </span>
                )}
              </div>

              {/* Actions */}
              {!isOwnProfile && (
                <div className="flex flex-col gap-2 sm:flex-row sm:gap-2">
                  <Button
                    onClick={handleSaveContact}
                    variant={isSaved ? "outline" : "default"}
                    className="font-medium px-6 py-3 flex items-center gap-2"
                    data-testid="save-contact-btn"
                  >
                    <BookmarkSimple size={20} weight={isSaved ? 'fill' : 'duotone'} />
                    {isSaved ? 'Saved' : 'Save Contact'}
                  </Button>
                  <Button
                    onClick={copyAllInfo}
                    variant="outline"
                    className="font-medium px-6 py-3 flex items-center gap-2"
                    data-testid="copy-info-btn"
                  >
                    <Copy size={20} weight="duotone" />
                    Copy Info
                  </Button>
                </div>
              )}
              {isOwnProfile && (
                <Link
                  to="/profile"
                  className="bg-primary text-primary-foreground font-medium px-6 py-3 rounded-md hover:bg-primary/90 transition-all"
                >
                  Edit Profile
                </Link>
              )}
            </div>
          </div>

          {/* Bio */}
          {user.bio && (
            <div className="p-8 border-b border-border">
              <h2 className="text-xs tracking-widest uppercase font-semibold text-primary mb-3">About</h2>
              <p className="text-foreground/80 leading-relaxed">{user.bio}</p>
            </div>
          )}

          {/* Looking For */}
          {user.looking_for && (
            <div className="p-8 border-b border-border">
              <h2 className="text-xs tracking-widest uppercase font-semibold text-primary mb-3">Looking For</h2>
              <p className="text-foreground/80 leading-relaxed">{user.looking_for}</p>
            </div>
          )}

          {/* Interests */}
          {user.interests && user.interests.length > 0 && (
            <div className="p-8 border-b border-border">
              <h2 className="text-xs tracking-widest uppercase font-semibold text-primary mb-3">Interests</h2>
              <div className="flex flex-wrap gap-2">
                {user.interests.map((interest, i) => (
                  <span key={i} className="bg-muted text-foreground text-sm px-3 py-1 rounded-full">
                    {interest}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Contact Info */}
          <div className="p-8 border-b border-border">
            <h2 className="text-xs tracking-widest uppercase font-semibold text-primary mb-4">Contact</h2>
            <div className="space-y-3">
              {user.email && (
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3 text-foreground/80">
                    <EnvelopeSimple size={20} weight="duotone" className="text-primary" />
                    <span>{user.email}</span>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => copyToClipboard(user.email, 'Email')}
                    className="text-muted-foreground hover:text-foreground"
                    data-testid="copy-email-btn"
                  >
                    <Copy size={16} />
                  </Button>
                </div>
              )}
              {user.phone && (
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3 text-foreground/80">
                    <Phone size={20} weight="duotone" className="text-primary" />
                    <span>{user.phone}</span>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => copyToClipboard(user.phone, 'Phone')}
                    className="text-muted-foreground hover:text-foreground"
                  >
                    <Copy size={16} />
                  </Button>
                </div>
              )}
              {user.linkedin_url && (
                <div className="flex items-center justify-between">
                  <a 
                    href={user.linkedin_url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="flex items-center gap-3 text-foreground/80 hover:text-primary transition-colors"
                  >
                    <LinkedinLogo size={20} weight="duotone" className="text-primary" />
                    <span>LinkedIn Profile</span>
                  </a>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => copyToClipboard(user.linkedin_url, 'LinkedIn URL')}
                    className="text-muted-foreground hover:text-foreground"
                  >
                    <Copy size={16} />
                  </Button>
                </div>
              )}
            </div>
          </div>

          {/* Private Note (only for saved contacts) */}
          {isSaved && !isOwnProfile && (
            <div className="p-8">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-xs tracking-widest uppercase font-semibold text-primary flex items-center gap-2">
                  <NotePencil size={16} weight="duotone" />
                  Private Note
                </h2>
                {!editingNote && note && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setEditingNote(true)}
                    className="text-muted-foreground hover:text-foreground"
                  >
                    Edit
                  </Button>
                )}
              </div>
              {editingNote || !note ? (
                <div className="space-y-3">
                  <Textarea
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    placeholder="Add a private note about this contact (e.g., where you met, conversation topics, follow-up items)..."
                    className="resize-none"
                    rows={4}
                    data-testid="note-textarea"
                  />
                  <div className="flex gap-2">
                    <Button
                      onClick={handleSaveNote}
                      disabled={savingNote}
                      className="font-medium px-4 py-2"
                      data-testid="save-note-btn"
                    >
                      {savingNote ? 'Saving...' : (
                        <>
                          <Check size={16} className="mr-2" />
                          Save Note
                        </>
                      )}
                    </Button>
                    {editingNote && (
                      <Button
                        onClick={() => setEditingNote(false)}
                        variant="ghost"
                        className="text-muted-foreground hover:text-foreground"
                      >
                        Cancel
                      </Button>
                    )}
                  </div>
                </div>
              ) : (
                <p className="text-foreground/80 bg-muted p-4 rounded-lg border border-border">{note}</p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default UserProfilePage;
