-- Analytical queries on the canteen data.
USE smart_canteen;

-- Q1. Menu with category and profit per unit (2-table join).
SELECT c.Category_Name, f.Food_Name, f.Selling_Price, f.Selling_Price - f.Preparation_Cost AS Margin
FROM food_item f JOIN category c ON c.Category_ID = f.Category_ID
ORDER BY c.Category_Name, f.Food_Name;

-- Q2. Current stock with category (3-table join).
SELECT c.Category_Name, f.Food_Name, i.Quantity_Available
FROM inventory i JOIN food_item f ON f.Food_ID = i.Food_ID JOIN category c ON c.Category_ID = f.Category_ID
ORDER BY i.Quantity_Available DESC;

-- Q3. Top 5 items by revenue in the last 30 days (4-table join, GROUP BY, LIMIT).
SELECT f.Food_Name, c.Category_Name, SUM(si.Quantity * si.Selling_Price) AS Revenue
FROM sale_item si JOIN sale s ON s.Sale_ID = si.Sale_ID
JOIN food_item f ON f.Food_ID = si.Food_ID JOIN category c ON c.Category_ID = f.Category_ID
WHERE s.Sale_Date >= CURDATE() - INTERVAL 30 DAY
GROUP BY f.Food_Name, c.Category_Name ORDER BY Revenue DESC LIMIT 5;

-- Q4. Bills and revenue per day, last 7 days (aggregate functions).
SELECT Sale_Date, COUNT(*) AS Bills, SUM(Total_Amount) AS Revenue, ROUND(AVG(Total_Amount), 2) AS Avg_Bill
FROM sale WHERE Sale_Date >= CURDATE() - INTERVAL 7 DAY
GROUP BY Sale_Date ORDER BY Sale_Date;

-- Q5. WASTE ALERT: items wasting more than 20 % in the last 30 days (HAVING).
SELECT Food_Name, SUM(Wasted) AS Wasted, ROUND(SUM(Wasted) * 100 / SUM(Quantity_Prepared), 1) AS Waste_Pct
FROM v_daily_waste WHERE Demand_Date >= CURDATE() - INTERVAL 30 DAY
GROUP BY Food_Name HAVING Waste_Pct > 20 ORDER BY Waste_Pct DESC;

-- Q6. Categories that lost more than Rs 10,000 to waste (3-table join, HAVING).
SELECT c.Category_Name, SUM(w.Quantity_Wasted) AS Units, SUM(w.Estimated_Loss) AS Loss
FROM waste_record w JOIN food_item f ON f.Food_ID = w.Food_ID JOIN category c ON c.Category_ID = f.Category_ID
GROUP BY c.Category_Name HAVING Loss > 10000 ORDER BY Loss DESC;

-- Q7. Cooked items with NO waste in the last 3 days (NOT EXISTS subquery).
SELECT Food_Name FROM food_item f
WHERE Is_Perishable = TRUE AND NOT EXISTS (
    SELECT 1 FROM waste_record w WHERE w.Food_ID = f.Food_ID AND w.Waste_Date >= CURDATE() - INTERVAL 3 DAY);

-- Q8. Items selling more than the average item (subquery in HAVING).
SELECT Food_Name, SUM(Quantity_Sold) AS Sold FROM v_daily_waste GROUP BY Food_Name
HAVING Sold > (SELECT AVG(total) FROM (SELECT SUM(Quantity_Sold) AS total FROM daily_demand GROUP BY Food_ID) t)
ORDER BY Sold DESC;

-- Q9. Each item's best day ever (correlated subquery: runs once per outer row).
SELECT f.Food_Name, d.Demand_Date, d.Quantity_Sold
FROM daily_demand d JOIN food_item f ON f.Food_ID = d.Food_ID
WHERE d.Quantity_Sold = (SELECT MAX(d2.Quantity_Sold) FROM daily_demand d2 WHERE d2.Food_ID = d.Food_ID)
ORDER BY d.Quantity_Sold DESC;

-- Q10. Yesterday's sales compared with each item's own average (correlated subquery).
SELECT f.Food_Name, d.Quantity_Sold,
       (SELECT ROUND(AVG(d2.Quantity_Sold), 1) FROM daily_demand d2 WHERE d2.Food_ID = d.Food_ID) AS Usual
FROM daily_demand d JOIN food_item f ON f.Food_ID = d.Food_ID
WHERE d.Demand_Date = CURDATE() - INTERVAL 1 DAY;

-- Q11. Rank items inside each category by units sold (window function RANK).
SELECT Category_Name, Food_Name, SUM(Quantity_Sold) AS Sold,
       RANK() OVER (PARTITION BY Category_Name ORDER BY SUM(Quantity_Sold) DESC) AS Rank_In_Category
FROM v_daily_waste GROUP BY Category_Name, Food_Name;

-- Q12. Change in revenue from the previous day (window function LAG).
SELECT Sale_Date, SUM(Total_Amount) AS Revenue,
       SUM(Total_Amount) - LAG(SUM(Total_Amount)) OVER (ORDER BY Sale_Date) AS Change_From_Yesterday
FROM sale WHERE Sale_Date >= CURDATE() - INTERVAL 14 DAY
GROUP BY Sale_Date ORDER BY Sale_Date;

-- Q13. Demand band for each item (CASE).
SELECT Food_Name, Avg_Daily_Sold,
       CASE WHEN Avg_Daily_Sold >= 40 THEN 'High' WHEN Avg_Daily_Sold >= 20 THEN 'Medium' ELSE 'Low' END AS Demand
FROM v_item_performance ORDER BY Avg_Daily_Sold DESC;

-- Q14. Sell-out days in the last 7 days (CASE inside SUM). 3 or more -> cook more.
SELECT Food_Name, SUM(CASE WHEN Quantity_Sold = Quantity_Prepared THEN 1 ELSE 0 END) AS Sold_Out_Days
FROM v_daily_waste WHERE Is_Perishable = TRUE AND Demand_Date >= CURDATE() - INTERVAL 7 DAY
GROUP BY Food_Name ORDER BY Sold_Out_Days DESC;

-- Q15. Waste % on weekdays vs weekends per category (CASE pivot).
SELECT Category_Name,
       ROUND(SUM(CASE WHEN WEEKDAY(Demand_Date) < 5 THEN Wasted END) * 100
           / SUM(CASE WHEN WEEKDAY(Demand_Date) < 5 THEN Quantity_Prepared END), 1) AS Weekday_Waste_Pct,
       ROUND(SUM(CASE WHEN WEEKDAY(Demand_Date) >= 5 THEN Wasted END) * 100
           / SUM(CASE WHEN WEEKDAY(Demand_Date) >= 5 THEN Quantity_Prepared END), 1) AS Weekend_Waste_Pct
FROM v_daily_waste WHERE Is_Perishable = TRUE GROUP BY Category_Name;

-- Q16. Average waste % for each day of the week (GROUP BY a date function).
SELECT DAYNAME(Demand_Date) AS Day, ROUND(SUM(Wasted) * 100 / SUM(Quantity_Prepared), 1) AS Waste_Pct
FROM v_daily_waste WHERE Is_Perishable = TRUE
GROUP BY WEEKDAY(Demand_Date), Day ORDER BY WEEKDAY(Demand_Date);

-- Q17. Forecast accuracy: recommendation in force vs what sold (empty until recommendations are used).
SELECT f.Food_Name, ROUND(AVG(ABS(d.Estimated_Demand - d.Quantity_Sold)), 1) AS Avg_Error
FROM daily_demand d JOIN food_item f ON f.Food_ID = d.Food_ID
WHERE d.Estimated_Demand IS NOT NULL GROUP BY f.Food_Name;

-- Q18. Spending per supplier per month (join, GROUP BY two columns).
SELECT s.Supplier_Name, DATE_FORMAT(p.Purchase_Date, '%Y-%m') AS Month, SUM(p.Total_Amount) AS Spent
FROM purchase p JOIN supplier s ON s.Supplier_ID = p.Supplier_ID
GROUP BY s.Supplier_Name, Month ORDER BY Month;

-- Q19. Which supplier supplies each packaged item (4-table join, DISTINCT).
SELECT DISTINCT f.Food_Name, s.Supplier_Name
FROM purchase_item pi JOIN purchase p ON p.Purchase_ID = pi.Purchase_ID
JOIN supplier s ON s.Supplier_ID = p.Supplier_ID JOIN food_item f ON f.Food_ID = pi.Food_ID;

-- Q20. The views and procedures.
SELECT * FROM v_monthly_loss;
SELECT * FROM v_low_stock;
SELECT * FROM v_supplier_summary;
CALL sp_item_report(1, CURDATE() - INTERVAL 7 DAY, CURDATE());
