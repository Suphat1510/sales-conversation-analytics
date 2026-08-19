-- 1) Conversation volume by product
SELECT product_type, COUNT(*) AS conversations
FROM conversations
GROUP BY product_type;

-- 2) Top customer needs
SELECT c.product_type, t.tag_name, COUNT(DISTINCT t.conversation_key) AS conversations
FROM conversation_tags t
JOIN conversations c USING(conversation_key)
WHERE t.tag_type = 'need'
GROUP BY c.product_type, t.tag_name
ORDER BY conversations DESC;

-- 3) Average first response time
SELECT c.product_type,
       ROUND(AVG(m.first_response_minutes), 2) AS avg_first_response_minutes
FROM conversation_metrics m
JOIN conversations c USING(conversation_key)
WHERE m.first_response_minutes IS NOT NULL
GROUP BY c.product_type;

-- 4) Purchase signals
SELECT c.product_type, t.tag_name, COUNT(DISTINCT t.conversation_key) AS conversations
FROM conversation_tags t
JOIN conversations c USING(conversation_key)
WHERE t.tag_type = 'purchase_signal'
GROUP BY c.product_type, t.tag_name
ORDER BY conversations DESC;
