-- triggers.sql - keeps stock and bill/purchase totals correct automatically.
-- Stock comes IN from production (daily_demand) and purchases,
-- and goes OUT through bills (and at close of day, in sp_close_day).
-- DELIMITER $$ lets the trigger bodies contain ';' (also works in Workbench).

DELIMITER $$

-- 1. Every new food item gets an inventory row with 0 stock.
CREATE TRIGGER trg_food_item_after_insert
AFTER INSERT ON food_item
FOR EACH ROW
BEGIN
    INSERT INTO inventory (Food_ID, Quantity_Available) VALUES (NEW.Food_ID, 0);
END$$

-- 2. A purchase line adds to stock and to the purchase total.
CREATE TRIGGER trg_purchase_item_after_insert
AFTER INSERT ON purchase_item
FOR EACH ROW
BEGIN
    UPDATE inventory SET Quantity_Available = Quantity_Available + NEW.Quantity
    WHERE Food_ID = NEW.Food_ID;
    UPDATE purchase SET Total_Amount = Total_Amount + NEW.Quantity * NEW.Unit_Price
    WHERE Purchase_ID = NEW.Purchase_ID;
END$$

-- 3. A bill line is refused if there is not enough stock.
CREATE TRIGGER trg_sale_item_before_insert
BEFORE INSERT ON sale_item
FOR EACH ROW
BEGIN
    DECLARE v_stock INT;
    DECLARE v_msg VARCHAR(255);
    SELECT Quantity_Available INTO v_stock FROM inventory WHERE Food_ID = NEW.Food_ID;
    IF v_stock < NEW.Quantity THEN
        SET v_msg = CONCAT('Not enough stock: only ', v_stock, ' left.');
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = v_msg;
    END IF;
END$$

-- 4. A bill line takes the food out of stock and adds to the bill total.
CREATE TRIGGER trg_sale_item_after_insert
AFTER INSERT ON sale_item
FOR EACH ROW
BEGIN
    UPDATE inventory SET Quantity_Available = Quantity_Available - NEW.Quantity
    WHERE Food_ID = NEW.Food_ID;
    UPDATE sale SET Total_Amount = Total_Amount + NEW.Quantity * NEW.Selling_Price
    WHERE Sale_ID = NEW.Sale_ID;
END$$

-- 5. If no loss is given, estimate it as quantity x preparation cost.
CREATE TRIGGER trg_waste_record_before_insert
BEFORE INSERT ON waste_record
FOR EACH ROW
BEGIN
    IF NEW.Estimated_Loss IS NULL THEN
        SET NEW.Estimated_Loss = NEW.Quantity_Wasted *
            (SELECT Preparation_Cost FROM food_item WHERE Food_ID = NEW.Food_ID);
    END IF;
END$$

-- 6. Morning production puts the cooked food into stock.
--    Closed rows (written at close of day or imported from CSV) are history
--    and must not change today's stock.
CREATE TRIGGER trg_daily_demand_after_insert
AFTER INSERT ON daily_demand
FOR EACH ROW
BEGIN
    IF NEW.Is_Closed = FALSE THEN
        UPDATE inventory SET Quantity_Available = Quantity_Available + NEW.Quantity_Prepared
        WHERE Food_ID = NEW.Food_ID;
    END IF;
END$$

-- 7. Editing today's production moves stock by the difference
--    (50 -> 60 adds 10). A decrease is refused if that food is already sold.
CREATE TRIGGER trg_daily_demand_before_update
BEFORE UPDATE ON daily_demand
FOR EACH ROW
BEGIN
    DECLARE v_diff INT DEFAULT NEW.Quantity_Prepared - OLD.Quantity_Prepared;
    IF OLD.Is_Closed = FALSE AND v_diff <> 0 THEN
        IF (SELECT Quantity_Available FROM inventory WHERE Food_ID = NEW.Food_ID) + v_diff < 0 THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'Cannot reduce production below what is already sold.';
        END IF;
        UPDATE inventory SET Quantity_Available = Quantity_Available + v_diff
        WHERE Food_ID = NEW.Food_ID;
    END IF;
END$$

DELIMITER ;
