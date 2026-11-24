-- procedures.sql - stored procedures.
--
-- sp_close_day is run inside ONE transaction by the caller:
--   Python:    app/db.py transaction() commits it, or rolls everything back on error
--   Workbench: START TRANSACTION;  CALL sp_close_day('2026-11-24');  COMMIT;

DELIMITER $$

-- End of day: record what was sold, throw away cooked leftovers,
-- and write one row for each packaged item. Returns the day's summary.
CREATE PROCEDURE sp_close_day(IN p_date DATE)
BEGIN
    IF EXISTS (SELECT 1 FROM daily_demand WHERE Demand_Date = p_date AND Is_Closed = TRUE) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'This day is already closed.';
    END IF;

    -- 1. Units sold today, from the bills.
    UPDATE daily_demand d
    SET d.Quantity_Sold = (SELECT COALESCE(SUM(si.Quantity), 0)
                           FROM sale_item si JOIN sale s ON s.Sale_ID = si.Sale_ID
                           WHERE si.Food_ID = d.Food_ID AND s.Sale_Date = p_date)
    WHERE d.Demand_Date = p_date;

    -- 2. Cooked food left in stock is wasted, and its stock goes back to 0.
    INSERT INTO waste_record (Food_ID, Waste_Date, Quantity_Wasted, Reason)
    SELECT i.Food_ID, p_date, i.Quantity_Available, 'Unsold at close'
    FROM inventory i JOIN food_item f ON f.Food_ID = i.Food_ID
    WHERE f.Is_Perishable = TRUE AND i.Quantity_Available > 0;

    UPDATE inventory i JOIN food_item f ON f.Food_ID = i.Food_ID
    SET i.Quantity_Available = 0
    WHERE f.Is_Perishable = TRUE;

    -- 3. Packaged items keep their stock; record sold and on-hand for the day.
    INSERT INTO daily_demand (Food_ID, Demand_Date, Quantity_Prepared, Quantity_Sold, Is_Closed)
    SELECT f.Food_ID, p_date, i.Quantity_Available + t.Sold, t.Sold, TRUE
    FROM food_item f
    JOIN inventory i ON i.Food_ID = f.Food_ID
    JOIN (SELECT si.Food_ID, SUM(si.Quantity) AS Sold
          FROM sale_item si JOIN sale s ON s.Sale_ID = si.Sale_ID
          WHERE s.Sale_Date = p_date GROUP BY si.Food_ID) t ON t.Food_ID = f.Food_ID
    WHERE f.Is_Perishable = FALSE;

    -- 4. Mark the day closed and show the summary.
    UPDATE daily_demand SET Is_Closed = TRUE WHERE Demand_Date = p_date;

    SELECT Food_Name, Quantity_Prepared, Quantity_Sold, Wasted, Waste_Pct, Loss
    FROM v_daily_waste WHERE Demand_Date = p_date ORDER BY Food_Name;
END$$

-- Day-by-day report for one item, with a TOTAL row at the end (WITH ROLLUP).
CREATE PROCEDURE sp_item_report(IN p_food_id INT, IN p_from DATE, IN p_to DATE)
BEGIN
    SELECT COALESCE(Demand_Date, 'TOTAL') AS Day,
           SUM(Quantity_Prepared) AS Prepared,
           SUM(Quantity_Sold)     AS Sold,
           SUM(Wasted)            AS Wasted,
           SUM(Loss)              AS Loss
    FROM v_daily_waste
    WHERE Food_ID = p_food_id AND Demand_Date BETWEEN p_from AND p_to
    GROUP BY Demand_Date WITH ROLLUP;
END$$

DELIMITER ;
