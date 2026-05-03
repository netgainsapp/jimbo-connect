import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Camera, Check, User, Buildings, Briefcase, MagnifyingGlass, LinkedinLogo, Phone, Users } from '@phosphor-icons/react';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

const INDUSTRIES = [
  'Technology',
  'Finance',
  'Healthcare',
  'Real Estate',
  'Marketing',
  'Consulting',
  'Legal',
  'Education',
  'Manufacturing',
  'Retail',
  'Media & Entertainment',
  'Non-profit',
  'Other',
];

const ProfilePage = () => {
  const { user, checkAuth } = useAuth();
  const navigate = useNavigate();
  const fileInputRef = useRef(null);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [profile, setProfile] = useState({
    name: '',
    role_title: '',
    company: '',
    bio: '',
    looking_for: '',
    industry: '',
    interests: [],
    linkedin_url: '',
    phone: '',
    table_cohort: '',
  });
  const [interestInput, setInterestInput] = useState('');
  const [profilePhoto, setProfilePhoto] = useState(null);

  useEffect(() => {
    if (user) {
      setProfile({
        name: user.name || '',
        role_title: user.role_title || '',
        company: user.company || '',
        bio: user.bio || '',
        looking_for: user.looking_for || '',
        industry: user.industry || '',
        interests: user.interests || [],
        linkedin_url: user.linkedin_url || '',
        phone: user.phone || '',
        table_cohort: user.table_cohort || '',
      });
      setProfilePhoto(user.profile_photo);
    }
  }, [user]);

  const handlePhotoUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      toast.error('Please select an image file');
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      toast.error('Image must be less than 5MB');
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await axios.post(`${API}/api/profile/photo`, formData, {
        withCredentials: true,
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setProfilePhoto(res.data.path);
      toast.success('Photo uploaded successfully');
      await checkAuth();
    } catch (error) {
      toast.error('Failed to upload photo');
    } finally {
      setUploading(false);
    }
  };

  const handleAddInterest = () => {
    if (interestInput.trim() && !profile.interests.includes(interestInput.trim())) {
      setProfile(prev => ({
        ...prev,
        interests: [...prev.interests, interestInput.trim()],
      }));
      setInterestInput('');
    }
  };

  const handleRemoveInterest = (interest) => {
    setProfile(prev => ({
      ...prev,
      interests: prev.interests.filter(i => i !== interest),
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      await axios.put(`${API}/api/profile`, profile, { withCredentials: true });
      toast.success('Profile updated successfully');
      await checkAuth();
    } catch (error) {
      toast.error('Failed to update profile');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background pt-24 px-6 pb-12">
      <div className="max-w-2xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-semibold text-foreground mb-2">Edit Profile</h1>
          <p className="text-muted-foreground">Help others understand who you are and what you're looking for</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-8">
          {/* Profile Photo */}
          <div className="flex items-center gap-6">
            <div className="relative">
              <div className="w-24 h-24 rounded-lg overflow-hidden bg-muted border border-border">
                {profilePhoto ? (
                  <img
                    src={`${API}/api/files/${profilePhoto}`}
                    alt="Profile"
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center bg-primary/10">
                    <User size={40} weight="duotone" className="text-primary" />
                  </div>
                )}
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handlePhotoUpload}
                className="hidden"
              />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                className="absolute -bottom-2 -right-2 w-8 h-8 bg-primary rounded-full flex items-center justify-center hover:bg-primary/90 transition-colors disabled:opacity-50"
                data-testid="upload-photo-btn"
              >
                <Camera size={16} weight="bold" className="text-primary-foreground" />
              </button>
            </div>
            <div>
              <p className="text-foreground font-medium">Profile Photo</p>
              <p className="text-muted-foreground text-sm">JPG, PNG or GIF. Max 5MB.</p>
            </div>
          </div>

          {/* Basic Info */}
          <div className="bg-card border border-border p-6 rounded-lg space-y-4">
            <h2 className="text-lg font-semibold text-foreground flex items-center gap-2">
              <User size={20} weight="duotone" className="text-primary" />
              Basic Information
            </h2>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Full Name *</Label>
                <Input
                  value={profile.name}
                  onChange={(e) => setProfile({ ...profile, name: e.target.value })}
                  required
                  data-testid="profile-name"
                />
              </div>
              <div className="space-y-2">
                <Label>Email</Label>
                <Input
                  value={user?.email || ''}
                  disabled
                  className="text-muted-foreground"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label>Bio</Label>
              <Textarea
                value={profile.bio}
                onChange={(e) => setProfile({ ...profile, bio: e.target.value })}
                placeholder="Tell people about yourself..."
                className="resize-none"
                rows={3}
                data-testid="profile-bio"
              />
            </div>
          </div>

          {/* Professional Info */}
          <div className="bg-card border border-border p-6 rounded-lg space-y-4">
            <h2 className="text-lg font-semibold text-foreground flex items-center gap-2">
              <Briefcase size={20} weight="duotone" className="text-primary" />
              Professional Details
            </h2>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Job Title</Label>
                <Input
                  value={profile.role_title}
                  onChange={(e) => setProfile({ ...profile, role_title: e.target.value })}
                  placeholder="e.g., Product Manager"
                  data-testid="profile-role"
                />
              </div>
              <div className="space-y-2">
                <Label>Company</Label>
                <Input
                  value={profile.company}
                  onChange={(e) => setProfile({ ...profile, company: e.target.value })}
                  placeholder="e.g., Acme Inc."
                  data-testid="profile-company"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label>Industry</Label>
              <Select 
                value={profile.industry} 
                onValueChange={(value) => setProfile({ ...profile, industry: value })}
              >
                <SelectTrigger data-testid="profile-industry">
                  <SelectValue placeholder="Select your industry" />
                </SelectTrigger>
                <SelectContent>
                  {INDUSTRIES.map(ind => (
                    <SelectItem key={ind} value={ind}>{ind}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Table / Cohort</Label>
              <Input
                value={profile.table_cohort}
                onChange={(e) => setProfile({ ...profile, table_cohort: e.target.value })}
                placeholder="e.g., Table 5, Group A"
                data-testid="profile-table"
              />
            </div>
          </div>

          {/* What You're Looking For */}
          <div className="bg-card border border-border p-6 rounded-lg space-y-4">
            <h2 className="text-lg font-semibold text-foreground flex items-center gap-2">
              <MagnifyingGlass size={20} weight="duotone" className="text-primary" />
              Networking Goals
            </h2>
            
            <div className="space-y-2">
              <Label>What are you looking for?</Label>
              <Textarea
                value={profile.looking_for}
                onChange={(e) => setProfile({ ...profile, looking_for: e.target.value })}
                placeholder="e.g., Looking for co-founders, investors, mentors, partnerships..."
                className="resize-none"
                rows={3}
                data-testid="profile-looking-for"
              />
            </div>

            <div className="space-y-2">
              <Label>Interests</Label>
              <div className="flex gap-2">
                <Input
                  value={interestInput}
                  onChange={(e) => setInterestInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddInterest())}
                  placeholder="Add an interest and press Enter"
                  data-testid="profile-interest-input"
                />
                <Button
                  type="button"
                  onClick={handleAddInterest}
                  variant="secondary"
                >
                  Add
                </Button>
              </div>
              {profile.interests.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-2">
                  {profile.interests.map((interest, i) => (
                    <span
                      key={i}
                      className="bg-muted text-foreground text-sm px-3 py-1 rounded-full flex items-center gap-2"
                    >
                      {interest}
                      <button
                        type="button"
                        onClick={() => handleRemoveInterest(interest)}
                        className="text-muted-foreground hover:text-foreground"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Contact Info */}
          <div className="bg-card border border-border p-6 rounded-lg space-y-4">
            <h2 className="text-lg font-semibold text-foreground flex items-center gap-2">
              <Users size={20} weight="duotone" className="text-primary" />
              Contact Information
            </h2>
            
            <div className="space-y-2">
              <Label>LinkedIn URL</Label>
              <div className="relative">
                <LinkedinLogo size={20} weight="duotone" className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <Input
                  value={profile.linkedin_url}
                  onChange={(e) => setProfile({ ...profile, linkedin_url: e.target.value })}
                  placeholder="https://linkedin.com/in/yourprofile"
                  className="pl-12"
                  data-testid="profile-linkedin"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label>Phone Number</Label>
              <div className="relative">
                <Phone size={20} weight="duotone" className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <Input
                  value={profile.phone}
                  onChange={(e) => setProfile({ ...profile, phone: e.target.value })}
                  placeholder="+1 (555) 123-4567"
                  className="pl-12"
                  data-testid="profile-phone"
                />
              </div>
            </div>
          </div>

          {/* Submit */}
          <Button
            type="submit"
            disabled={loading}
            className="w-full py-4 font-medium flex items-center justify-center gap-2"
            data-testid="save-profile-btn"
          >
            {loading ? 'Saving...' : (
              <>
                <Check size={20} weight="bold" />
                Save Profile
              </>
            )}
          </Button>
        </form>
      </div>
    </div>
  );
};

export default ProfilePage;
