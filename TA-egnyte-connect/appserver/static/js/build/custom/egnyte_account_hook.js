class AccountHook {
    constructor(globalConfig, serviceName, state, mode, util) {
		this.globalConfig = globalConfig;
		this.serviceName = serviceName;
		this.state = state;
		this.mode = mode;
		this.util = util;
	}
	/*
		Put logic here to execute javascript on UI creation.
	*/
	onChange(field, value, dataDict) {
        this.util.setState((prevState) => {
            let data = { ...prevState.data };
            data.client_id.markdownMessage = {
            text: "Generate Code",
            link: `https://${dataDict.data.egnyte_domain.value}/puboauth/token?client_id=${dataDict.data.client_id.value}&no_redirect=true&response_type=code&scope=Egnyte.audit&redirect_uri=https://www.egnyte.com`,
            markdownType: "link",
            };
            return { data };
        });
	}
 
	onRender() {
        
        this.util.setState((prevState) => {
            let data = { ...prevState.data };
            data.client_id.markdownMessage = {
            text: "Generate Code",
            link: `https:///puboauth/token?client_id=&no_redirect=true&response_type=code&scope=Egnyte.audit&redirect_uri=https://www.egnyte.com"`,
            markdownType: "link",
            };
            return { data };
        });
 
 
	}
 
	isEmpty(value) {
		/* Returns true if value is not set else false */
		return value === null || value.trim().length === 0;
	}
}
 
export default AccountHook;