-- Update user to be active
UPDATE warder.users 
SET is_active = true 
WHERE username = 'testuser';
