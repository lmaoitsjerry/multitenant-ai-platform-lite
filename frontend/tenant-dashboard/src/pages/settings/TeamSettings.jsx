import { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { usersApi } from '../../services/api';
import {
  UserPlusIcon,
  PencilSquareIcon,
  TrashIcon,
  XMarkIcon,
  CheckCircleIcon,
  ClockIcon,
  ExclamationCircleIcon,
  ArrowPathIcon,
  EnvelopeIcon,
} from '@heroicons/react/24/outline';

// Confirmation Modal Component
function ConfirmModal({ isOpen, title, message, confirmText, cancelText, onConfirm, onCancel, danger }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl max-w-md w-full mx-4 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-2">{title}</h3>
        <p className="text-gray-600 mb-6">{message}</p>
        <div className="flex gap-3">
          <button
            onClick={onCancel}
            className="btn-secondary flex-1"
          >
            {cancelText || 'Cancel'}
          </button>
          <button
            onClick={onConfirm}
            className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors ${
              danger
                ? 'bg-red-600 text-white hover:bg-red-700'
                : 'bg-primary-600 text-white hover:bg-primary-700'
            }`}
          >
            {confirmText || 'Confirm'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function TeamSettings() {
  const { user: currentUser, isAdmin } = useAuth();
  const [users, setUsers] = useState([]);
  const [invitations, setInvitations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [toast, setToast] = useState(null);

  // Modal states
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  const [confirmModal, setConfirmModal] = useState({ isOpen: false, title: '', message: '', onConfirm: null, danger: false });

  // Form states
  const [inviteForm, setInviteForm] = useState({ email: '', name: '', role: 'consultant' });
  const [editForm, setEditForm] = useState({ name: '', role: '' });
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (isAdmin) {
      loadData();
    }
  }, [isAdmin]);

  const loadData = async () => {
    setLoading(true);
    setError('');
    try {
      const [usersRes, invitationsRes] = await Promise.all([
        usersApi.list(),
        usersApi.listInvitations(),
      ]);
      setUsers(usersRes.data.users || []);
      setInvitations(invitationsRes.data.invitations || []);
    } catch (err) {
      setError('Failed to load team data');
      console.error('Error loading team data:', err);
    } finally {
      setLoading(false);
    }
  };

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  // Invite user
  const handleInvite = async (e) => {
    e.preventDefault();
    if (!inviteForm.email || !inviteForm.name) return;

    setSubmitting(true);
    try {
      await usersApi.invite(inviteForm.email, inviteForm.name, inviteForm.role);
      showToast(`Invitation sent to ${inviteForm.email}`);
      setInviteForm({ email: '', name: '', role: 'consultant' });
      setShowInviteModal(false);
      loadData();
    } catch (err) {
      showToast(err.response?.data?.detail || 'Failed to send invitation', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  // Edit user
  const handleEdit = async (e) => {
    e.preventDefault();
    if (!selectedUser) return;

    setSubmitting(true);
    try {
      await usersApi.update(selectedUser.id, editForm);
      showToast('User updated successfully');
      setShowEditModal(false);
      setSelectedUser(null);
      loadData();
    } catch (err) {
      showToast(err.response?.data?.detail || 'Failed to update user', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  // Deactivate user
  const handleDeactivate = (userId, userName) => {
    setConfirmModal({
      isOpen: true,
      title: 'Deactivate User',
      message: `Are you sure you want to deactivate ${userName}? They will no longer be able to access the platform.`,
      confirmText: 'Deactivate',
      danger: true,
      onConfirm: async () => {
        setConfirmModal({ ...confirmModal, isOpen: false });
        try {
          await usersApi.deactivate(userId);
          showToast('User deactivated successfully');
          loadData();
        } catch (err) {
          showToast(err.response?.data?.detail || 'Failed to deactivate user', 'error');
        }
      }
    });
  };

  // Cancel invitation
  const handleCancelInvitation = (invitationId, email) => {
    setConfirmModal({
      isOpen: true,
      title: 'Cancel Invitation',
      message: `Cancel invitation for ${email}?`,
      confirmText: 'Cancel Invitation',
      danger: true,
      onConfirm: async () => {
        setConfirmModal({ ...confirmModal, isOpen: false });
        try {
          await usersApi.cancelInvitation(invitationId);
          showToast('Invitation cancelled');
          loadData();
        } catch (err) {
          showToast(err.response?.data?.detail || 'Failed to cancel invitation', 'error');
        }
      }
    });
  };

  // Resend invitation
  const handleResendInvitation = async (invitationId) => {
    try {
      await usersApi.resendInvitation(invitationId);
      showToast('Invitation resent');
      loadData();
    } catch (err) {
      showToast(err.response?.data?.detail || 'Failed to resend invitation', 'error');
    }
  };

  const openEditModal = (user) => {
    setSelectedUser(user);
    setEditForm({ name: user.name, role: user.role });
    setShowEditModal(true);
  };

  if (!isAdmin) {
    return (
      <div className="text-center py-12">
        <ExclamationCircleIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900">Admin Access Required</h3>
        <p className="text-gray-500 mt-1">Only administrators can manage team members.</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-theme">Team Members</h3>
          <p className="text-sm text-theme-muted">
            {users.length} member{users.length !== 1 ? 's' : ''} in your organization
          </p>
        </div>
        <button
          onClick={() => setShowInviteModal(true)}
          className="btn-primary flex items-center gap-2"
        >
          <UserPlusIcon className="w-5 h-5" />
          Invite Member
        </button>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 text-red-500 px-4 py-3 rounded-lg">
          {error}
        </div>
      )}

      {/* Users Table */}
      <div className="card overflow-hidden p-0">
        <table className="min-w-full divide-y divide-theme">
          <thead className="bg-theme-surface-elevated">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-theme-muted uppercase tracking-wider">
                User
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-theme-muted uppercase tracking-wider">
                Role
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-theme-muted uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-theme-muted uppercase tracking-wider">
                Last Login
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-theme-muted uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-theme">
            {users.map((user) => {
              const isCurrentUser = user.id === currentUser?.id;
              return (
              <tr
                key={user.id}
                className={`
                  transition-colors duration-150
                  ${isCurrentUser
                    ? 'bg-theme-primary/5 border-l-2 border-theme-primary'
                    : 'border-l-2 border-transparent hover:bg-theme-surface-elevated'
                  }
                `}
              >
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center">
                    <div className="flex-shrink-0 h-10 w-10">
                      <div className="h-10 w-10 rounded-full bg-theme-primary/20 flex items-center justify-center">
                        <span className="text-theme-primary font-medium">
                          {user.name.charAt(0).toUpperCase()}
                        </span>
                      </div>
                    </div>
                    <div className="ml-4">
                      <div className="flex items-center gap-2 text-sm font-medium text-theme">
                        {user.name}
                        {isCurrentUser && (
                          <span className="text-xs font-medium text-theme-primary bg-theme-primary/10 px-2 py-0.5 rounded-full">
                            You
                          </span>
                        )}
                      </div>
                      <div className="text-sm text-theme-muted">{user.email}</div>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    user.role === 'admin'
                      ? 'bg-theme-primary/15 text-theme-primary'
                      : 'bg-theme-border text-theme-secondary'
                  }`}>
                    {user.role.charAt(0).toUpperCase() + user.role.slice(1)}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {user.is_active ? (
                    <span className="inline-flex items-center gap-1 text-green-500 text-sm">
                      <CheckCircleIcon className="w-4 h-4" />
                      Active
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-theme-muted text-sm">
                      <ExclamationCircleIcon className="w-4 h-4" />
                      Inactive
                    </span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-theme-muted">
                  {user.last_login_at
                    ? new Date(user.last_login_at).toLocaleDateString()
                    : 'Never'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  {!isCurrentUser && (
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => openEditModal(user)}
                        className="text-theme-muted hover:text-theme-primary transition-colors"
                        title="Edit user"
                      >
                        <PencilSquareIcon className="w-5 h-5" />
                      </button>
                      <button
                        onClick={() => handleDeactivate(user.id, user.name)}
                        className="text-theme-muted hover:text-red-500 transition-colors"
                        title="Deactivate user"
                      >
                        <TrashIcon className="w-5 h-5" />
                      </button>
                    </div>
                  )}
                </td>
              </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Pending Invitations */}
      {invitations.length > 0 && (
        <div className="card">
          <h4 className="font-semibold text-theme mb-4 flex items-center gap-2">
            <ClockIcon className="w-5 h-5 text-amber-500" />
            Pending Invitations
          </h4>
          <div className="space-y-3">
            {invitations.map((invitation) => (
              <div
                key={invitation.id}
                className="flex items-center justify-between p-4 bg-amber-500/10 border border-amber-500/30 rounded-lg"
              >
                <div className="flex items-center gap-3">
                  <EnvelopeIcon className="w-5 h-5 text-amber-500" />
                  <div>
                    <p className="font-medium text-theme">{invitation.name}</p>
                    <p className="text-sm text-theme-muted">{invitation.email}</p>
                  </div>
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                    invitation.role === 'admin'
                      ? 'bg-theme-primary/15 text-theme-primary'
                      : 'bg-theme-border text-theme-secondary'
                  }`}>
                    {invitation.role}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-theme-muted">
                    Expires {new Date(invitation.expires_at).toLocaleDateString()}
                  </span>
                  <button
                    onClick={() => handleResendInvitation(invitation.id)}
                    className="text-amber-500 hover:text-amber-400 transition-colors"
                    title="Resend invitation"
                  >
                    <ArrowPathIcon className="w-5 h-5" />
                  </button>
                  <button
                    onClick={() => handleCancelInvitation(invitation.id, invitation.email)}
                    className="text-red-500 hover:text-red-400 transition-colors"
                    title="Cancel invitation"
                  >
                    <XMarkIcon className="w-5 h-5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Invite Modal */}
      {showInviteModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full mx-4 p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold text-gray-900">Invite Team Member</h3>
              <button
                onClick={() => setShowInviteModal(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <XMarkIcon className="w-6 h-6" />
              </button>
            </div>

            <form onSubmit={handleInvite} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Name
                </label>
                <input
                  type="text"
                  value={inviteForm.name}
                  onChange={(e) => setInviteForm({ ...inviteForm, name: e.target.value })}
                  required
                  className="input"
                  placeholder="John Doe"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email
                </label>
                <input
                  type="email"
                  value={inviteForm.email}
                  onChange={(e) => setInviteForm({ ...inviteForm, email: e.target.value })}
                  required
                  className="input"
                  placeholder="john@example.com"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Role
                </label>
                <select
                  value={inviteForm.role}
                  onChange={(e) => setInviteForm({ ...inviteForm, role: e.target.value })}
                  className="input"
                >
                  <option value="consultant">Consultant</option>
                  <option value="admin">Admin</option>
                </select>
                <p className="mt-1 text-xs text-gray-500">
                  Consultants can manage quotes and invoices. Admins can also manage team members and settings.
                </p>
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowInviteModal(false)}
                  className="btn-secondary flex-1"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="btn-primary flex-1"
                >
                  {submitting ? 'Sending...' : 'Send Invitation'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {showEditModal && selectedUser && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full mx-4 p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold text-gray-900">Edit User</h3>
              <button
                onClick={() => {
                  setShowEditModal(false);
                  setSelectedUser(null);
                }}
                className="text-gray-400 hover:text-gray-600"
              >
                <XMarkIcon className="w-6 h-6" />
              </button>
            </div>

            <form onSubmit={handleEdit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Name
                </label>
                <input
                  type="text"
                  value={editForm.name}
                  onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                  required
                  className="input"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email
                </label>
                <input
                  type="email"
                  value={selectedUser.email}
                  disabled
                  className="input bg-gray-50"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Role
                </label>
                <select
                  value={editForm.role}
                  onChange={(e) => setEditForm({ ...editForm, role: e.target.value })}
                  className="input"
                >
                  <option value="consultant">Consultant</option>
                  <option value="admin">Admin</option>
                </select>
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => {
                    setShowEditModal(false);
                    setSelectedUser(null);
                  }}
                  className="btn-secondary flex-1"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="btn-primary flex-1"
                >
                  {submitting ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Confirmation Modal */}
      <ConfirmModal
        isOpen={confirmModal.isOpen}
        title={confirmModal.title}
        message={confirmModal.message}
        confirmText={confirmModal.confirmText}
        danger={confirmModal.danger}
        onConfirm={confirmModal.onConfirm}
        onCancel={() => setConfirmModal({ ...confirmModal, isOpen: false })}
      />

      {/* Toast */}
      {toast && (
        <div className={`fixed bottom-4 right-4 flex items-center gap-2 px-4 py-3 rounded-lg shadow-lg z-50 ${
          toast.type === 'success' ? 'bg-green-600 text-white' : 'bg-red-600 text-white'
        }`}>
          {toast.type === 'success' ? (
            <CheckCircleIcon className="w-5 h-5" />
          ) : (
            <ExclamationCircleIcon className="w-5 h-5" />
          )}
          {toast.message}
        </div>
      )}
    </div>
  );
}
