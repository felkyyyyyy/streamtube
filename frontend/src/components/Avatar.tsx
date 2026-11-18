import React from 'react';

interface AvatarProps {
  name: string;
  color: string;
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
}

const SIZE_MAP = {
  xs: 'w-6 h-6 text-xs',
  sm: 'w-8 h-8 text-xs',
  md: 'w-9 h-9 text-sm',
  lg: 'w-12 h-12 text-lg',
  xl: 'w-20 h-20 text-3xl',
};

export const Avatar: React.FC<AvatarProps> = ({ name, color, size = 'md' }) => {
  const initial = (name || '?').trim().charAt(0).toUpperCase();
  return (
    <div
      style={{ backgroundColor: color || '#e11d48' }}
      className={`${SIZE_MAP[size]} rounded-full flex items-center justify-center font-semibold text-white shrink-0 select-none shadow-sm`}
      aria-hidden="true"
    >
      {initial}
    </div>
  );
};
