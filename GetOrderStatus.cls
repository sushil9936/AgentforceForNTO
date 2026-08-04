public with sharing class GetOrderStatus {

    // ---- What the agent SENDS us (the tool's input) ----
    public class Request {
        @InvocableVariable(label='Order Number' required=true)
        public String orderNumber;
    }

    // ---- What we RETURN to the agent (the tool's output) ----
    public class Response {
        @InvocableVariable public Boolean found;
        @InvocableVariable public String orderNumber;
        @InvocableVariable public String status;
        @InvocableVariable public String item;
        @InvocableVariable public String deliveryDate;
        @InvocableVariable public String trackingNumber;
    }

    @InvocableMethod(
        label='Get Order Status'
        description='Looks up an NTO order by its order number and returns its status and shipping details.'
    )
    public static List<Response> getOrderStatus(List<Request> requests) {
        List<Response> responses = new List<Response>();

        for (Request req : requests) {
            Response res = new Response();
            res.orderNumber = req.orderNumber;

            // Query the custom object for the matching order number
            List<NTO_Order__c> orders = [
                SELECT Name, Status__c, Item__c, Delivery_Date__c, Tracking_Number__c
                FROM NTO_Order__c
                WHERE Name = :req.orderNumber
                LIMIT 1
            ];

            if (orders.isEmpty()) {
                res.found = false;
            } else {
                NTO_Order__c o = orders[0];
                res.found = true;
                res.status = o.Status__c;
                res.item = o.Item__c;
                res.deliveryDate = (o.Delivery_Date__c == null)
                    ? null
                    : String.valueOf(o.Delivery_Date__c);
                res.trackingNumber = o.Tracking_Number__c;
            }
            responses.add(res);
        }
        return responses;
    }
}
