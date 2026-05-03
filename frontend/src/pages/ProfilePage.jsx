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
    <div className="min-h-screen bg-[#0A0D14] pt-24 px-6 pb-12">
      <div className="max-w-2xl mx-auto">
        <div className="mb-8">
          <h1 className="font-['Playfair_Display'] text-3xl text-white mb-2">Edit Profile</h1>
          <p className="text-white/60">Help others understand who you are and what you're looking for</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-8">
          {/* Profile Photo */}
          <div className="flex items-center gap-6">
            <div className="relative">
              <div className="w-24 h-24 rounded-sm overflow-hidden bg-[#121621] border border-white/10">
                {profilePhoto ? (
                  <img
                    src={`${API}/api/files/${profilePhoto}`}
                    alt="Profile"
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center bg-[#D4AF37]/20">
                    <User size={40} weight="duotone" className="text-[#D4AF37]" />
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
                className="absolute -bottom-2 -right-2 w-8 h-8 bg-[#D4AF37] rounded-full flex items-center justify-center hover:bg-[#F0C84B] transition-colors disabled:opacity-50"
                data-testid="upload-photo-btn"
              >
                <Camera size={16} weight="bold" className="text-[#0A0D14]" />
              </button>
            </div>
            <div>
              <p className="text-white font-medium">Profile Photo</p>
              <p className="text-white/60 text-sm">JPG, PNG or GIF. Max 5MB.</p>
            </div>
          </div>

          {/* Basic Info */}
          <div className="bg-[#121621] border border-white/5 p-6 rounded-sm space-y-4">
            <h2 className="font-['Playfair_Display'] text-lg text-white flex items-center gap-2">
              <User size={20} weight="duotone" className="text-[#D4AF37]" />
              Basic Information
            </h2>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="text-white/80">Full Name *</Label>
                <Input
                  value={profile.name}
                  onChange={(e) => setProfile({ ...profile, name: e.target.value })}
                  className="bg-[#0A0D14] border-white/10 text-white"
                  required
                  data-testid="profile-name"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-white/80">Email</Label>
                <Input
                  value={user?.email || ''}
                  disabled
                  className="bg-[#0A0D14] border-white/10 text-white/60"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label className="text-white/80">Bio</Label>
              <Textarea
                value={profile.bio}
                onChange={(e) => setProfile({ ...profile, bio: e.target.value })}
                placeholder="Tell people about yourself..."
                className="bg-[#0A0D14] border-white/10 text-white resize-none"
                rows={3}
                data-testid="profile-bio"
              />
            </div>
          </div>

          {/* Professional Info */}
          <div className="bg-[#121621] border border-white/5 p-6 rounded-sm space-y-4">
            <h2 className="font-['Playfair_Display'] text-lg text-white flex items-center gap-2">
              <Briefcase size={20} weight="duotone" className="text-[#D4AF37]" />
              Professional Details
            </h2>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="text-white/80">Job Title</Label>
                <Input
                  value={profile.role_title}
                  onChange={(e) => setProfile({ ...profile, role_title: e.target.value })}
                  placeholder="e.g., Product Manager"
                  className="bg-[#0A0D14] border-white/10 text-white"
                  data-testid="profile-role"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-white/80">Company</Label>
                <Input
                  value={profile.company}
                  onChange={(e) => setProfile({ ...profile, company: e.target.value })}
                  placeholder="e.g., Acme Inc."
                  className="bg-[#0A0D14] border-white/10 text-white"
                  data-testid="profile-company"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label className="text-white/80">Industry</Label>
              <Select 
                value={profile.industry} 
                onValueChange={(value) => setProfile({ ...profile, industry: value })}
              >
                <SelectTrigger className="bg-[#0A0D14] border-white/10 text-white" data-testid="profile-industry">
                  <SelectValue placeholder="Select your industry" />
                </SelectTrigger>
                <SelectContent className="bg-[#121621] border-white/10">
                  {INDUSTRIES.map(ind => (
                    <SelectItem key={ind} value={ind}>{ind}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label className="text-white/80">Table / Cohort</Label>
              <Input
                value={profile.table_cohort}
                onChange={(e) => setProfile({ ...profile, table_cohort: e.target.value })}
                placeholder="e.g., Table 5, Group A"
                className="bg-[#0A0D14] border-white/10 text-white"
                data-testid="profile-table"
              />
            </div>
          </div>

          {/* What You're Looking For */}
          <div className="bg-[#121621] border border-white/5 p-6 rounded-sm space-y-4">
            <h2 className="font-['Playfair_Display'] text-lg text-white flex items-center gap-2">
              <MagnifyingGlass size={20} weight="duotone" className="text-[#D4AF37]" />
              Networking Goals
            </h2>
            
            <div className="space-y-2">
              <Label className="text-white/80">What are you looking for?</Label>
              <Textarea
                value={profile.looking_for}
                onChange={(e) => setProfile({ ...profile, looking_for: e.target.value })}
                placeholder="e.g., Looking for co-founders, investors, mentors, partnerships..."
                className="bg-[#0A0D14] border-white/10 text-white resize-none"
                rows={3}
                data-testid="profile-looking-for"
              />
            </div>

            <div className="space-y-2">
              <Label className="text-white/80">Interests</Label>
              <div className="flex gap-2">
                <Input
                  value={interestInput}
                  onChange={(e) => setInterestInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddInterest())}
                  placeholder="Add an interest and press Enter"
                  className="bg-[#0A0D14] border-white/10 text-white"
                  data-testid="profile-interest-input"
                />
                <Button
                  type="button"
                  onClick={handleAddInterest}
                  className="bg-white/10 text-white hover:bg-white/20"
                >
                  Add
                </Button>
              </div>
              {profile.interests.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-2">
                  {profile.interests.map((interest, i) => (
                    <span
                      key={i}
                      className="bg-white/10 text-white text-sm px-3 py-1 rounded-full flex items-center gap-2"
                    >
                      {interest}
                      <button
                        type="button"
                        onClick={() => handleRemoveInterest(interest)}
                        className="text-white/60 hover:text-white"
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
          <div className="bg-[#121621] border border-white/5 p-6 rounded-sm space-y-4">
            <h2 className="font-['Playfair_Display'] text-lg text-white flex items-center gap-2">
              <Users size={20} weight="duotone" className="text-[#D4AF37]" />
              Contact Information
            </h2>
            
            <div className="space-y-2">
              <Label className="text-white/80">LinkedIn URL</Label>
              <div className="relative">
                <LinkedinLogo size={20} weight="duotone" className="absolute left-4 top-1/2 -translate-y-1/2 text-white/40" />
                <Input
                  value={profile.linkedin_url}
                  onChange={(e) => setProfile({ ...profile, linkedin_url: e.target.value })}
                  placeholder="https://linkedin.com/in/yourprofile"
                  className="bg-[#0A0D14] border-white/10 text-white pl-12"
                  data-testid="profile-linkedin"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label className="text-white/80">Phone Number</Label>
              <div className="relative">
                <Phone size={20} weight="duotone" className="absolute left-4 top-1/2 -translate-y-1/2 text-white/40" />
                <Input
                  value={profile.phone}
                  onChange={(e) => setProfile({ ...profile, phone: e.target.value })}
                  placeholder="+1 (555) 123-4567"
                  className="bg-[#0A0D14] border-white/10 text-white pl-12"
                  data-testid="profile-phone"
                />
              </div>
            </div>
          </div>

          {/* Submit */}
          <Button
            type="submit"
            disabled={loading}
            className="w-full bg-[#D4AF37] text-[#0A0D14] font-medium py-4 rounded-sm hover:bg-[#F0C84B] transition-all disabled:opacity-50 flex items-center justify-center gap-2"
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
