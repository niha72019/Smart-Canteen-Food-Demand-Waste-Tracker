-- The 11 tables of the Smart Canteen database.

CREATE TABLE category (
    Category_ID   INT AUTO_INCREMENT PRIMARY KEY,
    Category_Name VARCHAR(50) NOT NULL UNIQUE
);

-- Is_Perishable: TRUE = cooked daily (leftovers are wasted), FALSE = packaged (stock carries over)
CREATE TABLE food_item (
    Food_ID          INT AUTO_INCREMENT PRIMARY KEY,
    Food_Name        VARCHAR(100) NOT NULL UNIQUE,
    Category_ID      INT NOT NULL,
    Selling_Price    DECIMAL(8,2) NOT NULL CHECK (Selling_Price >= 0),
    Preparation_Cost DECIMAL(8,2) NOT NULL CHECK (Preparation_Cost >= 0),
    Is_Perishable    BOOLEAN NOT NULL DEFAULT TRUE,
    FOREIGN KEY (Category_ID) REFERENCES category (Category_ID)
);

CREATE TABLE supplier (
    Supplier_ID   INT AUTO_INCREMENT PRIMARY KEY,
    Supplier_Name VARCHAR(100) NOT NULL,
    Contact       VARCHAR(20),
    Address       VARCHAR(255)
);

-- Total_Amount is kept up to date by a trigger.
CREATE TABLE purchase (
    Purchase_ID   INT AUTO_INCREMENT PRIMARY KEY,
    Supplier_ID   INT NOT NULL,
    Purchase_Date DATE NOT NULL,
    Total_Amount  DECIMAL(10,2) NOT NULL DEFAULT 0,
    FOREIGN KEY (Supplier_ID) REFERENCES supplier (Supplier_ID),
    INDEX (Purchase_Date)
);

CREATE TABLE purchase_item (
    Purchase_ID INT NOT NULL,
    Food_ID     INT NOT NULL,
    Quantity    INT NOT NULL CHECK (Quantity > 0),
    Unit_Price  DECIMAL(8,2) NOT NULL CHECK (Unit_Price >= 0),
    PRIMARY KEY (Purchase_ID, Food_ID),
    FOREIGN KEY (Purchase_ID) REFERENCES purchase (Purchase_ID),
    FOREIGN KEY (Food_ID) REFERENCES food_item (Food_ID)
);

-- One row per food item (UNIQUE Food_ID makes it 1:1).
CREATE TABLE inventory (
    Inventory_ID       INT AUTO_INCREMENT PRIMARY KEY,
    Food_ID            INT NOT NULL UNIQUE,
    Quantity_Available INT NOT NULL DEFAULT 0 CHECK (Quantity_Available >= 0),
    Last_Updated       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (Food_ID) REFERENCES food_item (Food_ID) ON DELETE CASCADE
);

-- Total_Amount is kept up to date by a trigger.
CREATE TABLE sale (
    Sale_ID      INT AUTO_INCREMENT PRIMARY KEY,
    Sale_Date    DATE NOT NULL,
    Total_Amount DECIMAL(10,2) NOT NULL DEFAULT 0,
    INDEX (Sale_Date)
);

-- Selling_Price is the price charged at the time of sale.
CREATE TABLE sale_item (
    Sale_ID       INT NOT NULL,
    Food_ID       INT NOT NULL,
    Quantity      INT NOT NULL CHECK (Quantity > 0),
    Selling_Price DECIMAL(8,2) NOT NULL CHECK (Selling_Price >= 0),
    PRIMARY KEY (Sale_ID, Food_ID),
    FOREIGN KEY (Sale_ID) REFERENCES sale (Sale_ID),
    FOREIGN KEY (Food_ID) REFERENCES food_item (Food_ID)
);

-- Estimated_Loss is filled by a trigger when left NULL.
CREATE TABLE waste_record (
    Waste_ID        INT AUTO_INCREMENT PRIMARY KEY,
    Food_ID         INT NOT NULL,
    Waste_Date      DATE NOT NULL,
    Quantity_Wasted INT NOT NULL CHECK (Quantity_Wasted > 0),
    Reason          VARCHAR(100) NOT NULL DEFAULT 'Unsold at close',
    Estimated_Loss  DECIMAL(10,2),
    FOREIGN KEY (Food_ID) REFERENCES food_item (Food_ID),
    INDEX (Waste_Date)
);

-- One row per item per day. For packaged items Quantity_Prepared is the quantity on hand;
-- Estimated_Demand is the recommendation in force that morning.
CREATE TABLE daily_demand (
    Demand_ID         INT AUTO_INCREMENT PRIMARY KEY,
    Food_ID           INT NOT NULL,
    Demand_Date       DATE NOT NULL,
    Quantity_Prepared INT NOT NULL DEFAULT 0 CHECK (Quantity_Prepared >= 0),
    Quantity_Sold     INT NOT NULL DEFAULT 0 CHECK (Quantity_Sold >= 0),
    Estimated_Demand  INT,
    Is_Closed         BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (Food_ID, Demand_Date),
    CONSTRAINT chk_sold_not_more_than_prepared CHECK (Quantity_Sold <= Quantity_Prepared),
    FOREIGN KEY (Food_ID) REFERENCES food_item (Food_ID),
    INDEX (Demand_Date)
);

-- Recommendation_Date is the day the quantity is meant for; Basis is the reason.
CREATE TABLE recommendation (
    Recommendation_ID    INT AUTO_INCREMENT PRIMARY KEY,
    Food_ID              INT NOT NULL,
    Recommendation_Date  DATE NOT NULL,
    Recommended_Quantity INT NOT NULL CHECK (Recommended_Quantity >= 0),
    Basis                VARCHAR(255) NOT NULL,
    UNIQUE (Food_ID, Recommendation_Date),
    FOREIGN KEY (Food_ID) REFERENCES food_item (Food_ID) ON DELETE CASCADE
);
