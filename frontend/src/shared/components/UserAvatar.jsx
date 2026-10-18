import { useRef } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { UserRound } from 'lucide-react';
import PropTypes from 'prop-types';
import { Avatar, AvatarFallback, AvatarImage } from './ui/avatar';
import { getApiAssetUrl } from '@/shared/services/api';
import { fetchUserProfile } from '@/shared/store/authSlice';

export default function UserAvatar({ src, className = '', refreshOnError = true }) {
  const user = useSelector(state => state.auth.user);
  const dispatch = useDispatch();
  const retriedAt = useRef(0);
  const source = src === undefined ? user?.avatar : src;
  const refresh = () => {
    if (!source || !refreshOnError || Date.now() - retriedAt.current < 60000) return;
    retriedAt.current = Date.now();
    dispatch(fetchUserProfile());
  };
  const initials = [user?.first_name, user?.last_name].filter(Boolean).map(name => name[0]).join('').slice(0, 2);
  return <Avatar className={className}><AvatarImage className="object-cover" src={getApiAssetUrl(source)} alt="Your profile photo" onLoadingStatusChange={status => { if (status === 'error') refresh(); }} /><AvatarFallback className="bg-brand/10 text-brand">{initials || <UserRound className="h-1/2 w-1/2" />}</AvatarFallback></Avatar>;
}
UserAvatar.propTypes = { src: PropTypes.string, className: PropTypes.string, refreshOnError: PropTypes.bool };
