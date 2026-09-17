import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { X, MessageSquare, CheckSquare2, AlertCircle, Send } from 'lucide-react';
import { DashboardLane, DashboardWorkProduct, Comment, fetchTaskComments, postTaskComment, updateChecklistItem } from '../services/api';

interface TaskDetailModalProps {
  task: DashboardWorkProduct;
  lane: DashboardLane;
  sessionId: string;
  onClose: () => void;
  onTaskUpdated: () => void;
}

type TabType = 'overview' | 'comments' | 'approvals';

export const TaskDetailModal: React.FC<TaskDetailModalProps> = ({
  task,
  lane,
  sessionId,
  onClose,
  onTaskUpdated,
}) => {
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [comments, setComments] = useState<Comment[]>([]);
  const [newComment, setNewComment] = useState('');
  const [isPosting, setIsPosting] = useState(false);

  useEffect(() => {
    fetchTaskComments(sessionId, task.key).then(setComments);
  }, [sessionId, task.key]);

  const handlePostComment = async () => {
    if (!newComment.trim()) return;
    setIsPosting(true);
    try {
      await postTaskComment(sessionId, task.key, 'human-reviewer', 'human', newComment);
      setNewComment('');
      const updated = await fetchTaskComments(sessionId, task.key);
      setComments(updated);
    } catch (e) {
      console.error('Failed to post comment', e);
    } finally {
      setIsPosting(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'NOT_STARTED': return 'bg-slate-500/20 text-slate-300 border-slate-500/30';
      case 'IN_PROGRESS': return 'bg-blue-500/20 text-blue-300 border-blue-500/30';
      case 'AWAITING_REVIEW': return 'bg-amber-500/20 text-amber-300 border-amber-500/30';
      case 'COMPLETED': return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30';
      default: return 'bg-slate-500/20 text-slate-300 border-slate-500/30';
    }
  };

  return (
    <>
      {/* Backdrop */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-40" />

      {/* Modal */}
      <motion.div
        initial={{ x: '100%', opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        exit={{ x: '100%', opacity: 0 }}
        transition={{ type: 'spring', damping: 30, stiffness: 300 }}
        className="fixed right-0 top-0 bottom-0 w-full md:w-1/2 lg:w-2/5 bg-slate-900 border-l border-slate-800 z-50 flex flex-col overflow-hidden">

        {/* Header */}
        <div className="flex-shrink-0 bg-gradient-to-br from-slate-900 to-slate-800 border-b border-slate-700 px-6 py-5">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <h2 className="text-xl font-extrabold text-white truncate">{task.name}</h2>
              <div className="flex items-center gap-2 mt-2 flex-wrap">
                <span className={`px-2 py-1 rounded text-xs font-semibold border ${getStatusColor(task.status)}`}>
                  {task.status === 'NOT_STARTED' ? 'Not Started' :
                   task.status === 'IN_PROGRESS' ? 'In Progress' :
                   task.status === 'AWAITING_REVIEW' ? 'Awaiting Review' :
                   'Completed'}
                </span>
                <span className="px-2 py-1 rounded text-xs font-mono bg-slate-800 border border-slate-700 text-slate-300">
                  {task.phase}
                </span>
                <span className="px-2 py-1 rounded text-xs font-semibold text-slate-300 bg-slate-800 border border-slate-700">
                  {lane.name}
                </span>
              </div>
            </div>
            <button
              onClick={onClose}
              className="flex-shrink-0 p-2 rounded-lg hover:bg-slate-800 transition text-slate-400 hover:text-slate-200">
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex-shrink-0 border-b border-slate-800 flex bg-slate-900/50">
          <button
            onClick={() => setActiveTab('overview')}
            className={`flex-1 px-4 py-3 text-xs font-semibold transition border-b-2 ${
              activeTab === 'overview'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-slate-300'
            }`}>
            Overview
          </button>
          <button
            onClick={() => setActiveTab('comments')}
            className={`flex-1 px-4 py-3 text-xs font-semibold transition border-b-2 flex items-center justify-center gap-1 ${
              activeTab === 'comments'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-slate-300'
            }`}>
            <MessageSquare className="w-3.5 h-3.5" />
            Comments ({comments.length})
          </button>
          <button
            onClick={() => setActiveTab('approvals')}
            className={`flex-1 px-4 py-3 text-xs font-semibold transition border-b-2 flex items-center justify-center gap-1 ${
              activeTab === 'approvals'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-slate-300'
            }`}>
            <AlertCircle className="w-3.5 h-3.5" />
            Approvals
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {activeTab === 'overview' && (
            <div className="p-6 space-y-6">
              <div>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Description</h3>
                <p className="text-sm text-slate-300">
                  {task.name} — a key deliverable for this project phase. This task moves through the workflow from initial discovery through completion.
                </p>
              </div>

              <div>
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">Task Details</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Phase:</span>
                    <span className="font-semibold text-slate-200">{task.phase}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Owner Lane:</span>
                    <span className="font-semibold text-slate-200">{lane.name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Version:</span>
                    <span className="font-semibold text-slate-200">{task.version || '—'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Updated:</span>
                    <span className="font-semibold text-slate-200">
                      {task.updated_at ? new Date(task.updated_at).toLocaleString() : '—'}
                    </span>
                  </div>
                </div>
              </div>

              {task.checklist && task.checklist.length > 0 && (
                <div>
                  <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">Checklist</h3>
                  <div className="space-y-2">
                    {task.checklist.map(item => (
                      <ChecklistItemRow
                        key={item.id}
                        item={item}
                        taskKey={task.key}
                        sessionId={sessionId}
                        onUpdate={() => onTaskUpdated()}
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'comments' && (
            <div className="p-6 space-y-4 flex flex-col h-full">
              {/* Comments list */}
              <div className="flex-1 space-y-3 overflow-y-auto min-h-0">
                {comments.length === 0 ? (
                  <div className="text-center py-8 text-slate-500 text-sm">
                    No comments yet. Be the first to add one!
                  </div>
                ) : (
                  comments.map(comment => (
                    <div key={comment.id} className="rounded-lg bg-slate-800/50 border border-slate-700 p-3">
                      <div className="flex items-start gap-2 mb-1.5">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <span className="font-semibold text-xs text-slate-300">{comment.author}</span>
                            <span className={`text-[10px] px-1 py-0.5 rounded ${
                              comment.author_type === 'system' ? 'bg-slate-700 text-slate-400' :
                              comment.author_type === 'agent' ? 'bg-blue-900/40 text-blue-300' :
                              'bg-emerald-900/40 text-emerald-300'
                            }`}>
                              {comment.author_type === 'system' ? 'System' :
                               comment.author_type === 'agent' ? 'Agent' :
                               'Human'}
                            </span>
                          </div>
                          <p className="text-[10px] text-slate-500 mt-0.5">
                            {new Date(comment.timestamp).toLocaleString()}
                          </p>
                        </div>
                      </div>
                      <p className="text-sm text-slate-300 leading-relaxed">{comment.body}</p>
                    </div>
                  ))
                )}
              </div>

              {/* Comment input */}
              <div className="flex-shrink-0 space-y-2 border-t border-slate-800 pt-3">
                <textarea
                  value={newComment}
                  onChange={(e) => setNewComment(e.target.value)}
                  placeholder="Add a comment..."
                  rows={3}
                  className="w-full px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500/50 resize-none"
                />
                <button
                  onClick={handlePostComment}
                  disabled={isPosting || !newComment.trim()}
                  className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold text-sm transition">
                  <Send className="w-3.5 h-3.5" />
                  Post Comment
                </button>
              </div>
            </div>
          )}

          {activeTab === 'approvals' && (
            <div className="p-6 space-y-4">
              <div className={`rounded-lg p-4 border ${
                task.status === 'AWAITING_REVIEW'
                  ? 'bg-amber-500/10 border-amber-500/30'
                  : 'bg-emerald-500/10 border-emerald-500/30'
              }`}>
                {task.status === 'AWAITING_REVIEW' ? (
                  <>
                    <div className="flex items-start gap-2">
                      <AlertCircle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
                      <div>
                        <h4 className="font-semibold text-amber-300 text-sm">Awaiting Review</h4>
                        <p className="text-sm text-amber-200 mt-1">
                          This task is pending human review. Please review the task details, checklist items, and comments above before approving or requesting changes.
                        </p>
                      </div>
                    </div>
                    <div className="flex gap-2 mt-4">
                      <button className="flex-1 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-sm transition">
                        Approve
                      </button>
                      <button className="flex-1 px-4 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-200 font-semibold text-sm transition">
                        Request Changes
                      </button>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="flex items-start gap-2">
                      <AlertCircle className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
                      <div>
                        <h4 className="font-semibold text-emerald-300 text-sm">Status: {task.status}</h4>
                        <p className="text-sm text-emerald-200 mt-1">
                          This task is not currently awaiting review.
                        </p>
                      </div>
                    </div>
                  </>
                )}
              </div>
            </div>
          )}
        </div>
      </motion.div>
    </>
  );
};

interface ChecklistItemRowProps {
  item: any; // ChecklistItem
  taskKey: string;
  sessionId: string;
  onUpdate: () => void;
}

const ChecklistItemRow: React.FC<ChecklistItemRowProps> = ({ item, taskKey, sessionId, onUpdate }) => {
  const [isUpdating, setIsUpdating] = useState(false);

  const handleToggle = async () => {
    setIsUpdating(true);
    try {
      await updateChecklistItem(sessionId, taskKey, item.id, !item.completed);
      onUpdate();
    } catch (e) {
      console.error('Failed to update checklist item', e);
    } finally {
      setIsUpdating(false);
    }
  };

  return (
    <div className="flex items-start gap-3 p-2.5 rounded-lg bg-slate-800/30 border border-slate-700/50 hover:bg-slate-800/50 transition">
      <button
        onClick={handleToggle}
        disabled={isUpdating}
        className="flex-shrink-0 mt-0.5 disabled:opacity-50">
        <CheckSquare2 className={`w-5 h-5 transition ${
          item.completed ? 'text-emerald-400' : 'text-slate-600'
        }`} />
      </button>
      <div className="flex-1 min-w-0">
        <p className={`text-sm ${item.completed ? 'line-through text-slate-500' : 'text-slate-300'}`}>
          {item.text}
        </p>
        {item.verified_by && (
          <p className="text-[10px] text-slate-500 mt-1">Verified by {item.verified_by}</p>
        )}
      </div>
    </div>
  );
};
