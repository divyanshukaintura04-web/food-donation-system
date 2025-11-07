-- SCHEMA for Food Donation System
CREATE TABLE IF NOT EXISTS Admin (
    AdminID INTEGER PRIMARY KEY AUTOINCREMENT,
    Username TEXT UNIQUE NOT NULL,
    Password TEXT NOT NULL,
    Role TEXT
);

CREATE TABLE IF NOT EXISTS User (
    UserID INTEGER PRIMARY KEY AUTOINCREMENT,
    UserType TEXT CHECK(UserType IN ('NGO','Individual')) NOT NULL,
    Name TEXT NOT NULL,
    ContactNumber TEXT,
    Email TEXT,
    Address TEXT,
    ProofType TEXT,
    ProofNumber TEXT,
    Username TEXT UNIQUE NOT NULL,
    Password TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS Donor (
    DonorID INTEGER PRIMARY KEY AUTOINCREMENT,
    Name TEXT NOT NULL,
    Type TEXT,
    ContactNumber TEXT,
    Address TEXT
);

CREATE TABLE IF NOT EXISTS FoodItem (
    FoodID INTEGER PRIMARY KEY AUTOINCREMENT,
    DonorID INTEGER,
    FoodName TEXT,
    Quantity INTEGER,
    ExpiryDate TEXT,
    Status TEXT DEFAULT 'Available',
    FOREIGN KEY (DonorID) REFERENCES Donor(DonorID)
);

CREATE TABLE IF NOT EXISTS Request (
    ReqID INTEGER PRIMARY KEY AUTOINCREMENT,
    UserID INTEGER,
    FoodID INTEGER,
    ProofFile TEXT,
    RequestDate TEXT,
    Status TEXT DEFAULT 'Pending',
    Verified TEXT DEFAULT 'No',
    FOREIGN KEY (UserID) REFERENCES User(UserID),
    FOREIGN KEY (FoodID) REFERENCES FoodItem(FoodID)
);

CREATE TABLE IF NOT EXISTS Volunteer (
    VolID INTEGER PRIMARY KEY AUTOINCREMENT,
    Name TEXT NOT NULL,
    ContactNumber TEXT,
    NGOID INTEGER,
    FOREIGN KEY (NGOID) REFERENCES User(UserID)
);

CREATE TABLE IF NOT EXISTS Delivery (
    DeliveryID INTEGER PRIMARY KEY AUTOINCREMENT,
    ReqID INTEGER,
    VolID INTEGER,
    PickupTime TEXT,
    DeliveryTime TEXT,
    Status TEXT DEFAULT 'Picked',
    FOREIGN KEY (ReqID) REFERENCES Request(ReqID),
    FOREIGN KEY (VolID) REFERENCES Volunteer(VolID)
);

CREATE TABLE IF NOT EXISTS Feedback (
    FeedbackID INTEGER PRIMARY KEY AUTOINCREMENT,
    UserID INTEGER,
    DonorID INTEGER,
    Rating INTEGER,
    Comments TEXT,
    Date TEXT,
    FOREIGN KEY (UserID) REFERENCES User(UserID),
    FOREIGN KEY (DonorID) REFERENCES Donor(DonorID)
);
