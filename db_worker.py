import asyncpg
import asyncio
from datetime import datetime


class UserDatabaseManager:
    def __init__(self, dbname, user, password, host='192.168.1.117', port=5432):
        self.dbname = dbname
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(
            database=self.dbname,
            user=self.user,
            password=self.password,
            host=self.host,
            port=self.port
        )

    async def disconnect(self):
        if self.pool:
            await self.pool.close()

    async def create_user_account(self, user_data):
        if not self.pool:
            print("Database connection is not established.")
            return

        query = """
        INSERT INTO users (user_id, username, first_name, last_name, balance, trade_link, is_admin)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (user_id) DO NOTHING;
        """
        try:
            async with self.pool.acquire() as connection:
                await connection.execute(
                    query,
                    user_data['user_id'],
                    user_data.get('username'),
                    user_data.get('first_name'),
                    user_data.get('last_name'),
                    0.0,  # Initial balance
                    user_data.get('trade_link', ''),  # Default empty string if not provided
                    False
                )
                print("User account created or already exists")
        except Exception as e:
            print(f"Error creating user account: {e}")

    async def get_all_user_ids(self):
        if not self.pool:
            print("Database connection is not established.")
            return set()

        query = "SELECT user_id FROM users"
        try:
            async with self.pool.acquire() as connection:
                rows = await connection.fetch(query)
                user_ids = {row['user_id'] for row in rows}  # Преобразуем в множество
                return user_ids
        except Exception as e:
            print(f"Error fetching user IDs: {e}")
            return set()

    async def get_all_user_in_process(self):
        if not self.pool:
            print("Database connection is not established.")
            return set()

        query = "SELECT user_id FROM user_in_process"
        try:
            async with self.pool.acquire() as connection:
                rows = await connection.fetch(query)
                user_ids = {row['user_id'] for row in rows}
                return user_ids
        except Exception as e:
            print(f"Error fetching user IDs: {e}")
            return set()

    async def add_user_to_process(self, user_id):
        if not self.pool:
            print("Database connection is not established.")
            return

        query = """
        INSERT INTO user_in_process (user_id)
        VALUES ($1)
        ON CONFLICT (user_id) DO NOTHING;
        """
        try:
            async with self.pool.acquire() as connection:
                await connection.execute(query, user_id)
                print(f"User {user_id} added to process")
        except Exception as e:
            print(f"Error adding user to process: {e}")

    async def remove_user_from_process(self, user_id):
        if not self.pool:
            print("Database connection is not established.")
            return

        query = """
        DELETE FROM user_in_process
        WHERE user_id = $1
        """
        try:
            async with self.pool.acquire() as connection:
                await connection.execute(query, user_id)
                print(f"User {user_id} removed from process")
        except Exception as e:
            print(f"Error removing user from process: {e}")

    async def update_trade_link(self, user_id, trade_link, steam_nickname):
        if not self.pool:
            print("Database connection is not established.")
            return

        query = """
        UPDATE users
        SET trade_link = $1,
        steam_nickname = $2
        WHERE user_id = $3
        """
        try:
            async with self.pool.acquire() as connection:
                result = await connection.execute(query, trade_link, steam_nickname, user_id)
                if result:
                    print(f"Trade link updated for user_id {user_id}")
        except Exception as e:
            print(f"Error updating trade link: {e}")

    async def get_user_balance(self, user_id):
        if not self.pool:
            print("Database connection is not established.")
            return None

        query = "SELECT balance FROM users WHERE user_id = $1"
        try:
            async with self.pool.acquire() as connection:
                row = await connection.fetchrow(query, user_id)
                if row:
                    return row['balance']
                else:
                    print(f"User with user_id {user_id} not found")
                    return None
        except Exception as e:
            print(f"Error fetching user balance: {e}")
            return None

    async def user_is_admin(self, user_id):
        if not self.pool:
            print("Database connection is not established.")
            return None

        query = "SELECT is_admin FROM users WHERE user_id = $1"
        try:
            async with self.pool.acquire() as connection:
                row = await connection.fetchrow(query, user_id)
                if row:
                    return row['is_admin']
                else:
                    print(f"User with user_id {user_id} not found")
                    return None
        except Exception as e:
            print(f"Error fetching user balance: {e}")
            return None

    async def get_user_trade_link(self, user_id):
        if not self.pool:
            print("Database connection is not established.")
            return None

        query = "SELECT trade_link FROM users WHERE user_id = $1"
        try:
            async with self.pool.acquire() as connection:
                row = await connection.fetchrow(query, user_id)
                if row:
                    return row['trade_link']
                else:
                    print(f"User with user_id {user_id} not found")
                    return None
        except Exception as e:
            print(f"Error fetching user trade link: {e}")
            return None

    async def add_to_user_balance(self, user_id, amount):
        if not self.pool:
            print("Database connection is not established.")
            return

        query = """
        UPDATE users
        SET balance = balance + $1
        WHERE user_id = $2
        """
        try:
            async with self.pool.acquire() as connection:
                result = await connection.execute(query, amount, user_id)
                if result:
                    print(f"Added {amount} to user_id {user_id}'s balance")
        except Exception as e:
            print(f"Error adding to user balance: {e}")

    async def subtract_from_user_balance(self, user_id, amount):
        if not self.pool:
            print("Database connection is not established.")
            return

        query = """
        UPDATE users
        SET balance = balance - $1
        WHERE user_id = $2 AND balance >= $1
        """
        try:
            async with self.pool.acquire() as connection:
                result = await connection.execute(query, amount, user_id)
                if result:
                    print(f"Subtracted {amount} from user_id {user_id}'s balance")
                else:
                    print(f"Insufficient funds for user_id {user_id}")
        except Exception as e:
            print(f"Error subtracting from user balance: {e}")

    async def transaction_add(self, transac_data):
        if not self.pool:
            print("Database connection is not established.")
            return

        query = """
        INSERT INTO transacts (user_id, transaction_id, transaction_state, timestamp, price_rub, item_name, trade_link, status_code)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8);
        """
        try:
            async with self.pool.acquire() as connection:
                curr_dt = datetime.now()
                await connection.execute(
                    query,
                    transac_data['user_id'],
                    transac_data.get('custom_id'),
                    transac_data.get('transaction_state'),
                    int(round(curr_dt.timestamp())),
                    transac_data.get('price'),
                    transac_data.get('item_name'),
                    transac_data.get('trade_link'),
                    transac_data.get('status_code')
                )
                print("transaction added")
        except Exception as e:
            print(f"Error creating transac: {e}")

    async def update_transac_status(self, transaction_id, status_code, transaction_state):
        if not self.pool:
            print("Database connection is not established.")
            return

        query = """
        UPDATE transacts
        SET transaction_state = $1,
            status_code = $2
        WHERE transaction_id = $3
        """
        try:
            async with self.pool.acquire() as connection:
                result = await connection.execute(query, transaction_state, status_code, transaction_id)
                if result:
                    print(f"status updated for {transaction_state}")
        except Exception as e:
            print(f"Error updating status: {transaction_state}")

    async def create_invoice(self, invoice_data):
        if not self.pool:
            print("Database connection is not established.")
            return

        query = """
        INSERT INTO pay_in (user_id, chat_id, invoice_id, invoice_status, money_amount, creating_timestamp, last_change_timestamp, money_to_user)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8);
        """
        try:
            async with self.pool.acquire() as connection:
                curr_dt = datetime.now()
                await connection.execute(
                    query,
                    invoice_data['user_id'],
                    invoice_data['chat_id'],
                    invoice_data['invoice_id'],
                    invoice_data['invoice_status'],
                    invoice_data['money_amount'],
                    int(round(curr_dt.timestamp())),
                    int(round(curr_dt.timestamp())),
                    invoice_data['money_to_user']
                )
                print("transaction added")
        except Exception as e:
            print(f"Error creating transac: {e}")

    async def update_invoice_status(self, new_invoice_status, invoice_id):
        if not self.pool:
            print("Database connection is not established.")
            return
        query = """
        UPDATE pay_in
        SET invoice_status = $1,
        last_change_timestamp = $2
        WHERE invoice_id = $3
        """
        curr_dt = datetime.now()

        try:
            async with self.pool.acquire() as connection:
                result = await connection.execute(query, new_invoice_status, int(round(curr_dt.timestamp())),
                                                  invoice_id)
                if result:
                    print(f"status updated for {new_invoice_status}")
        except Exception as e:
            print(f"Error updating status: {new_invoice_status}")

    async def get_all_invoices(self):
        if not self.pool:
            print("Database connection is not established.")
            return set()

        query = "SELECT invoice_id, user_id, money_to_user, chat_id FROM pay_in WHERE invoice_status = 1"
        try:
            async with self.pool.acquire() as connection:
                rows = await connection.fetch(query)
                # Use tuples instead of lists for each row
                invoice_ids = {(row['invoice_id'], row['user_id'], row['money_to_user'], row['chat_id']) for row in
                               rows}
                return invoice_ids
        except Exception as e:
            print(f"Error fetching user IDs: {e}")
            return set()

    async def get_user_profile_data(self, user_id: int) -> list:
        if not self.pool:
            print("Database connection is not established.")
            return []

        success_query = """
        SELECT user_id, count(1) as trades_cnt 
        FROM public.transacts
        WHERE status_code = 3 AND user_id = $1
        GROUP BY user_id
        """

        failed_query = """
        SELECT user_id, count(1) as trades_cnt 
        FROM public.transacts
        WHERE status_code = 4 AND user_id = $1
        GROUP BY user_id
        """

        try:
            async with self.pool.acquire() as connection:
                # Fetch data for successful trades
                rows1 = await connection.fetch(success_query, user_id)
                # Fetch data for failed trades
                rows2 = await connection.fetch(failed_query, user_id)

                # Initialize trade counts
                success_count = 0
                failed_count = 0

                # Extract trade counts from results
                if rows1:
                    success_count = rows1[0]['trades_cnt']

                if rows2:
                    failed_count = rows2[0]['trades_cnt']

                # Create a list of trade counts
                user_data = [success_count, failed_count]

                return user_data

        except Exception as e:
            print(f"Error fetching user profile data: {e}")
            return []

    async def get_profile_user_data(self, user_id):
        if not self.pool:
            print("Database connection is not established.")
            return None

        query = "SELECT username, user_id, balance, trade_link, steam_nickname FROM users WHERE user_id = $1"
        try:
            async with self.pool.acquire() as connection:
                row = await connection.fetchrow(query, user_id)
                if row:
                    return row
                else:
                    print(f"User with user_id {user_id} not found")
                    return None
        except Exception as e:
            print(f"Error fetching user trade link: {e}")
            return None


    async def get_user_history(self, user_id):
        if not self.pool:
            print("Database connection is not established.")
            return None

        query = """SELECT user_id, timestamp, price_rub, item_name, status_code, trade_link, transaction_id 
FROM public.transacts
where user_id =  $1 and status_code is not null
order by timestamp desc
limit 20
"""
        try:
            async with self.pool.acquire() as connection:
                row = await connection.fetch(query, user_id)
                if row:
                    return row
                else:
                    print(f"User with user_id {user_id} not found")
                    return None
        except Exception as e:
            print(f"Error fetching user trade link: {e}")
            return None


async def main():
    db = UserDatabaseManager('pgsql', 'test', 'test')
    await db.connect()
    data = await db.get_user_history(2071440104)
    print(data)
    await db.disconnect()


# Запуск
if __name__ == "__main__":
    asyncio.run(main())
