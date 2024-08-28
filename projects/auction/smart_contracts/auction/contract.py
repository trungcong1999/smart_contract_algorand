from algopy import ARC4Contract, Account, Asset, Global, LocalState, String, Txn, UInt64, gtxn, itxn
from algopy.arc4 import abimethod


class Auction(ARC4Contract):
    #Auction
    #Start Price
    #Bid - Bid Price > Start Price
    #Bid - Bid Price > Previous Bidder
    #Bidder != Previous Bidder
    #Start Time - End Time
    # If Auction End -> End Time -> 0
    # Amount -> Claim

    def __init__(self) -> None:
        self.start_time = UInt64(0) #auction start
        self.end_time = UInt64(0) # auction end
        self.asa_amount = UInt64(0) #Tổng khối lượng đang có #1000 - bid price > asa amount
        self.asa = Asset() #Tokens -> VBI Tokens -> only one time
        self.previous_bidder = Account()
        self.claimble_amount = LocalState(UInt64, key="claim", description='the calimble amount') #key - value

    # Opt Asset
    @abimethod() # -> asset VBI token
    def opt_into_asset(self, asset: Asset) -> None: # Đưa sản phẩm đấu giá vào
        assert Txn.sender == Global.creator_address, "Only the creator have asset"

        assert self.asa_amount == 0, "ASA already opt in"

        self.asa = asset

        itxn.AssetTransfer(
            xfer_asset = asset,
            asset_receiver = Global.current_application_address,
        ).submit()
    # Start Auction
    @abimethod()
    def start_auction(self, starting_price: UInt64, duration: UInt64, axfer: gtxn.AssetTransferTransaction) -> None: # Bắt đầu đấu gía
        assert Txn.sender == Global.creator_address, "Auction must be started by the creator"

        assert self.end_time == 0, "Auction is already started"

        assert axfer.asset_receiver == Global.current_application_address, "Asset must be transferred to the application"

        self.asa_amount = starting_price
        self.end_time =  duration + Global.latest_timestamp
        # global -> Unix Time -> 012090924 + 10001
        self.previous_bidder = Txn.sender
    # Bids
    @abimethod()
    def bid(self, pay: gtxn.PaymentTransaction) -> None: # Đấu giá
        # Kiểm tra cái buổi đấu giá có kết thúc chưa
        assert Global.latest_timestamp <= self.end_time, "Auction is already ended"
        
        # verify payment
        assert Txn.sender == self. previous_bidder, "You are the previous bidder"
        assert Txn.sender == pay.sender, "Verify again"
        assert pay.amount > self.asa_amount, "Bid must be greater than the current bid"
        
        # set data on global state
        self.asa_amount = pay.amount
        self.previous_bidder = Txn.sender
        
        # update claimable amount
        self.claimble_amount[Txn.sender]  = pay.amount
                      
    # Claim Bids
    @abimethod()
    def claim_asset(self, asset: Asset) -> None: # Chuyển sản phẩm đấu giá cho người thắng cuộc
        assert Txn.sender == Global.creator_address, "Auction must be started by the creator"
        assert Global.latest_timestamp > self.end_time, "Auction is not ended yet"
        
        itxn.AssetTransfer(
            xfer_asset = asset,
            asset_receiver = self.previous_bidder,
            asset_close_to = self.previous_bidder,
            asset_amount = self.asa_amount
        ).submit()
        
    @abimethod()
    def claim_bids(self) -> None: # Chuyển tiền cho người thắng cuộc
        amount = self.claimble_amount[Txn.sender] # lấy được tokens
        if Txn.sender == self.previous_bidder:
            amount -= self.asa_amount # -asa amount
        itxn.Payment(
            amount = amount,
            receiver = Txn.sender
        ).submit()
    
    # Delete Application
    @abimethod(allow_actions=['DeleteApplication'])
    def delete_application(self) -> None:
        itxn.Payment(
            close_remainder_to= Global.creator_address,
            receiver= Global.creator_address,
        ).submit()
    
