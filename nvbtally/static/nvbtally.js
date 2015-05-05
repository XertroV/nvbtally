(function(){
    app = angular.module("nvbApp", [])

    app.controller('TabController', ['$log', function($log){
        var tab = this;
        tab.tabsLeft = ['info', 'resolutions', 'votes'];
        tab.tabsRight = ['about'];

        tab.set = function(t){
            tab.current = t;
            $log.log('Setting tab to: ' + t);
        }
        tab.set('info');

        tab.is = function(t){
            return (t == tab.current);
        }
    }]);

    app.controller('InfoCtrl', ['$log', '$http', function($log, $http){
        var info = this;


    }]);

})();