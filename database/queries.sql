SELECT * FROM users;



-- DELETE FROM users WHERE id = 2;
-- DELETE FROM users WHERE username = 'RAM';


to see dates command is

SELECT 
    p.id AS project_id,
    p.title,
    p.due_date,
    u.username AS contractor_name
FROM 
    projects p
JOIN 
    users u ON p.contractor_id = u.id
WHERE 
    p.status = 'Accepted'
    AND p.due_date IS NOT NULL;





to see daily progress and updates

SELECT 
    dp.id,
    dp.project_id,
    dp.day,
    dp.progress,
    dp.image_path,
    u.username AS contractor_name
FROM 
    daily_progress dp
JOIN 
    users u ON dp.contractor_id = u.id
ORDER BY 
    dp.day DESC;
