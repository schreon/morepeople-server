angular.module('matchmakingserverstatus', ['ui.bootstrap']);

function StatusConroller($scope, $timeout, Data) {
    $scope.data = [];

    (function tick() {
        $scope.data = Data.query(function(){
            $timeout(tick, 1000);
            console.log("Trick!");
        });
    })();
};