def email_template(first_name,start_date,start_time):
  html_content = f"""
<!DOCTYPE HTML PUBLIC "-//W3C//DTD XHTML 1.0 Transitional //EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
<!--[if gte mso 9]>
<xml>
  <o:OfficeDocumentSettings>
    <o:AllowPNG/>
    <o:PixelsPerInch>96</o:PixelsPerInch>
  </o:OfficeDocumentSettings>
</xml>
<![endif]-->
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="x-apple-disable-message-reformatting">
<!--[if !mso]>
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<![endif]-->
<title></title>
<!--[if !mso]>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans:wght@400;700" rel="stylesheet" type="text/css">
<![endif]-->
</head>
<body class="clean-body u_body" style="margin: 0;padding: 0;-webkit-text-size-adjust: 100%;background-color: #ffffff;color: #000000">
<!--[if IE]>
<div class="ie-container">
<![endif]-->
<!--[if mso]>
<div class="mso-container">
<![endif]-->
<table id="u_body" style="border-collapse: collapse;table-layout: fixed;border-spacing: 0;mso-table-lspace: 0pt;mso-table-rspace: 0pt;vertical-align: top;min-width: 320px;Margin: 0 auto;background-color: #ffffff;width:100%" cellpadding="0" cellspacing="0">
  <tbody>
    <tr style="vertical-align: top">
      <td style="word-break: break-word;border-collapse: collapse !important;vertical-align: top">
        <!--[if (mso)|(IE)]>
        <table width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
        <td align="center" style="background-color: #ffffff;">
        <![endif]-->
        <div class="u-row-container" style="padding: 0px;background-color: transparent">
          <div class="u-row" style="margin: 0 auto 0 0;min-width: 320px;max-width: 600px;overflow-wrap: break-word;word-wrap: break-word;word-break: break-word;background-color: transparent;">
            <div style="border-collapse: collapse;display: table;width: 100%;height: 100%;background-color: transparent;">
              <!--[if (mso)|(IE)]>
              <table width="100%" cellpadding="0" cellspacing="0" border="0">
              <tr>
              <td style="padding: 0px;background-color: transparent;" align="left">
              <table cellpadding="0" cellspacing="0" border="0" style="width:600px;">
              <tr style="background-color: transparent;">
              <![endif]-->
              <!--[if (mso)|(IE)]>
              <td align="center" width="600" style="width: 600px;padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;" valign="top">
              <![endif]-->
              <div class="u-col u-col-100" style="max-width: 320px;min-width: 600px;display: table-cell;vertical-align: top;">
                <div style="height: 100%;width: 100% !important;">
                  <!--[if (!mso)&(!IE)]>
                  <div style="box-sizing: border-box; height: 100%; padding: 0px;border-top: 0px solid transparent;border-left: 0px solid transparent;border-right: 0px solid transparent;border-bottom: 0px solid transparent;">
                  <!--<![endif]-->
                  <table style="font-family:'Noto Sans', sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0">
                    <tbody>
                      <tr>
                        <td style="overflow-wrap:break-word;word-break:break-word;padding:10px;font-family:'Noto Sans', sans-serif;" align="left">
                          <div style="font-size: 14px; line-height: 140%; text-align: left; word-wrap: break-word;">
                            <p style="font-size: 14px; line-height: 140%;">Hi {first_name},</p>
                            
                            <p style="font-size: 14px; line-height: 140%;">Thank you for scheduling a tour of Keepme Fit Club!</p>
                            <p style="font-size: 14px; line-height: 140%;">Tour Details:</p>
                            <p style="font-size: 14px; line-height: 140%; margin: 4px 3px;">🗓 Date: {start_date}</p>
                            <p style="font-size: 14px; line-height: 140%; margin: 4px 3px;">🕘 Time: {start_time}</p>
                            <p style="font-size: 14px; line-height: 140%; margin: 4px 3px;">👤 Guide: James Smith</p>
                            <p style="font-size: 14px; line-height: 140%;">We look forward to seeing you at the club.</p>
                            <p style="font-size: 14px; line-height: 140%;">Olivia</p>
                          </div>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                  <table style="font-family:'Noto Sans', sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0">
                    <tbody>
                      <tr>
                        <td style="overflow-wrap:break-word;word-break:break-word;padding:30px 10px 10px;font-family:'Noto Sans', sans-serif;" align="left">
                          <table width="100%" cellpadding="0" cellspacing="0" border="0">
                            <tr>
                              <td style="padding-right: 0px;padding-left: 0px;" align="left">
                                <a href="https://www.keepmefit.club/" target="_blank">
                                  <img align="left" border="0" src="https://www.keepmefit.club/logo.png" alt="" title="" style="outline: none;text-decoration: none;-ms-interpolation-mode: bicubic;clear: both;display: inline-block !important;border: none;height: auto;float: none;width: 100%;max-width: 201px;" width="201"/>
                                </a>
                              </td>
                            </tr>
                          </table>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                  <table style="font-family:'Noto Sans', sans-serif;" role="presentation" cellpadding="0" cellspacing="0" width="100%" border="0">
                    <tbody>
                      <tr>
                        <td style="overflow-wrap:break-word;word-break:break-word;padding:10px;font-family:'Noto Sans', sans-serif;" align="left">
                          <div style="font-size: 14px; line-height: 110%; text-align: left; word-wrap: break-word;">
                            <p style="line-height: 110%;">
                              <span style="font-size: 12px; line-height: 13.2px;">Keepme Fit Club, Copyright © 2024</span>
                            </p>
                            <p style="line-height: 110%;">
                              <span style="font-size: 12px; line-height: 13.2px;">71-75 Shelton Street Covent Garden, London UK, WC2H 9JQ</span>
                            </p>
                          </div>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                  <!--[if (!mso)&(!IE)]>
                  </div>
                  <!--<![endif]-->
                </div>
              </div>
              <!--[if (mso)|(IE)]>
              </td>
              <![endif]-->
              <!--[if (mso)|(IE)]>
              </tr>
              </table>
              </td>
              <![endif]-->
              <!--[if (mso)|(IE)]>
              </tr>
              </table>
              <![endif]-->
            </div>
          </div>
        </div>
        <!--[if (mso)|(IE)]>
        </td>
        </tr>
        </table>
        <![endif]-->
      </td>
    </tr>
  </tbody>
</table>
<!--[if IE]>
</div>
<![endif]-->
<!--[if mso]>
</div>
<![endif]-->
</body>
</html>
"""

  return html_content