-- views.sql - saved queries used by the app's reports.

-- 1. Waste per item per closed day.
--    Unsold cooked food is waste; unsold packaged food carries over, so it is not.
--    app/analysis.py calculates the same numbers and a test checks they agree.
CREATE VIEW v_daily_waste AS
SELECT d.Demand_Date, d.Food_ID, f.Food_Name, c.Category_Name, f.Is_Perishable,
       d.Quantity_Prepared,
       d.Quantity_Sold,
       d.Quantity_Prepared - d.Quantity_Sold                          AS Unsold,
       IF(f.Is_Perishable, d.Quantity_Prepared - d.Quantity_Sold, 0)  AS Wasted,
       ROUND(IF(f.Is_Perishable, d.Quantity_Prepared - d.Quantity_Sold, 0) * 100
             / NULLIF(d.Quantity_Prepared, 0), 2)                     AS Waste_Pct,
       IF(f.Is_Perishable, d.Quantity_Prepared - d.Quantity_Sold, 0)
             * f.Preparation_Cost                                     AS Loss
FROM daily_demand d
JOIN food_item f ON f.Food_ID = d.Food_ID
JOIN category c ON c.Category_ID = f.Category_ID
WHERE d.Is_Closed = TRUE;

-- 2. Lifetime totals per item (built on the view above).
CREATE VIEW v_item_performance AS
SELECT Food_ID, Food_Name, Category_Name, Is_Perishable,
       COUNT(*)                                       AS Days,
       SUM(Quantity_Prepared)                         AS Prepared,
       SUM(Quantity_Sold)                             AS Sold,
       SUM(Wasted)                                    AS Wasted,
       ROUND(SUM(Wasted) * 100 / SUM(Quantity_Prepared), 2) AS Waste_Pct,
       ROUND(AVG(Quantity_Sold), 1)                   AS Avg_Daily_Sold,
       SUM(CASE WHEN Quantity_Sold = Quantity_Prepared THEN 1 ELSE 0 END) AS Sold_Out_Days,
       SUM(Loss)                                      AS Loss
FROM v_daily_waste
GROUP BY Food_ID, Food_Name, Category_Name, Is_Perishable;

-- 3. Money lost to waste per month.
CREATE VIEW v_monthly_loss AS
SELECT DATE_FORMAT(Waste_Date, '%Y-%m') AS Month,
       SUM(Quantity_Wasted)             AS Quantity_Wasted,
       SUM(Estimated_Loss)              AS Loss
FROM waste_record
GROUP BY Month;

-- 4. Packaged items with less than 3 days of stock left
--    (based on average daily sales over the last 7 days).
--    The inner query (a derived table) works out each item's average first,
--    so the outer WHERE can compare stock with it.
CREATE VIEW v_low_stock AS
SELECT *
FROM (SELECT f.Food_ID, f.Food_Name, i.Quantity_Available,
             (SELECT ROUND(AVG(d.Quantity_Sold), 1) FROM daily_demand d
              WHERE d.Food_ID = f.Food_ID AND d.Demand_Date >= CURDATE() - INTERVAL 7 DAY) AS Avg_Daily_Sold
      FROM food_item f
      JOIN inventory i ON i.Food_ID = f.Food_ID
      WHERE f.Is_Perishable = FALSE) AS stock
WHERE Quantity_Available < 3 * COALESCE(Avg_Daily_Sold, 0);

-- 5. Purchases and spending per supplier.
CREATE VIEW v_supplier_summary AS
SELECT s.Supplier_ID, s.Supplier_Name, s.Contact,
       COUNT(p.Purchase_ID)             AS Purchases,
       COALESCE(SUM(p.Total_Amount), 0) AS Total_Spent,
       MAX(p.Purchase_Date)             AS Last_Purchase
FROM supplier s
LEFT JOIN purchase p ON p.Supplier_ID = s.Supplier_ID
GROUP BY s.Supplier_ID, s.Supplier_Name, s.Contact;
